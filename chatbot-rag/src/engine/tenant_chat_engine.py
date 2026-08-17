import time
from datetime import datetime, timezone
from typing import Any

from src.config.chatbot_config import ChatbotConfig
from src.api.schemas import ChatResponse
from src.service_manager import get_service_manager
from src.utils.log_helper import logger
from src.llm.query_rewriter import QueryRewriter

from src.llm.llm_orchestrator import TenantLLMOrchestrator
from src.llm.prompt_builder import TenantPromptBuilder
from src.llm.clarification_manager import TenantClarificationManager
from src.vector.vector_retriever import VectorRetriever
from src.chat.tenant_conversation_repository import TenantConversationRepository
from src.chat.conversation_manager import ConversationManager

class TenantChatEngine:
    """Isolated chat engine for a specific workspace:chatbot pair."""
    
    def __init__(self, config: ChatbotConfig):
        self.config = config
        shared = get_service_manager()
        
        # Initialize tenant-specific components
        self.llm = TenantLLMOrchestrator(config)
        self.prompt_builder = TenantPromptBuilder(config)
        self.vector_retriever = VectorRetriever(
            embedding_manager=shared.embedding_manager, 
            collection_name=config.collection_name,
            reranker=shared.vector_retriever.reranker
        )
        self.clarification_manager = TenantClarificationManager(
            llm_orchestrator=self.llm, 
            prompt_builder=self.prompt_builder
        )
        
        tenant_repo = TenantConversationRepository(config.workspace_id, config.chatbot_id)
        self.conversation_manager = ConversationManager(repository=tenant_repo, llm=self.llm)
        
        # Shared (stateless) components
        self.confidence_scorer = shared.confidence_scorer
        self.query_rewriter = QueryRewriter()
    
    def config_matches(self, other: ChatbotConfig) -> bool:
        """Check if config matches this engine's current config (for cache validation)."""
        return (
            self.config.workspace_id == other.workspace_id
            and self.config.chatbot_id == other.chatbot_id
            and self.config.llm_provider == other.llm_provider
            and self.config.llm_model == other.llm_model
            and self.config.llm_api_key == other.llm_api_key
            and self.config.system_prompt == other.system_prompt
            and self.config.tone_preset == other.tone_preset
        )
    
    async def process_message(
        self, message: str, history: list[dict], user_id: str
    ) -> dict[str, Any]:
        """Run the full RAG pipeline for a single message."""
        start_time = time.time()
        logger.info(f"Starting RAG pipeline for workspace={self.config.workspace_id}, chatbot={self.config.chatbot_id}")

        # 1. Process incoming conversation history from frontend payload
        logger.info("Processing incoming conversation history...")
        from src.models import Message as ChatMsg
        from datetime import datetime, timezone
        from src.utils.config_loader import get_config
        
        # The frontend sends history in descending order (newest first). Reverse it to ascending.
        if history:
            history.reverse()
            
        history_messages = []
        now = datetime.now(timezone.utc)
        for msg_dict in history:
            role = msg_dict.get("role")
            content = msg_dict.get("content")
            if role and content:
                # Use a dummy user_id since this is just for runtime summarization
                history_messages.append(ChatMsg(role=role, content=content, timestamp=now, user_id=0))
                
        hist_result = self.conversation_manager.format_history_for_chat(history_messages)
        if isinstance(hist_result, (tuple, list)) and len(hist_result) >= 4:
            conversation_history, was_summarized, summarized_count, summary_text = hist_result[:4]
        else:
            conversation_history = hist_result
            was_summarized, summarized_count, summary_text = False, 0, None

        if was_summarized:
            logger.info(f"History summarized: {summarized_count} older messages condensed.")
        
        # 2. Rewrite query if ambiguous
        logger.info("Rewriting query...")
        rewritten_query = self.query_rewriter.rewrite_query(message, conversation_history)
        logger.debug(f"Rewritten query: {rewritten_query}")
        
        # 3. Retrieve relevant chunks from tenant Qdrant collection
        logger.info(f"Retrieving vector chunks from collection={self.config.collection_name}...")
        try:
            context = self.vector_retriever.retrieve_with_reranking(
                query=rewritten_query,
                initial_k=10
            )
            logger.info(f"Retrieved {len(context)} chunks.")
        except Exception as e:
            logger.error(f"Vector retrieval failed: {e}")
            context = []
            
        context_log = []
        for c in context:
            src = c.metadata.get("source") if isinstance(c.metadata, dict) else getattr(c.metadata, "source", None)
            content_preview = c.content if isinstance(c.content, str) and len(c.content) <= 200 else (c.content[:200] + "..." if isinstance(c.content, str) else "")
            relevance = c.relevance_score if hasattr(c, "relevance_score") else c.get("relevance_score") if isinstance(c, dict) else None
            context_log.append({"content": content_preview, "source": src, "relevance": relevance})
            
        logger.debug(f"Retrieved context for query '{rewritten_query}': {context_log}")
        logger.debug(f"Context relevance scores: {[c.relevance_score if hasattr(c, 'relevance_score') else c.get('relevance_score') if isinstance(c, dict) else None for c in context]}")
        
        # Apply low-cutoff filter
        try:
            from src.utils.config_loader import get_config
            low_cutoff = float(get_config("rag.low_cutoff", default=0.0))
            
            def _relevance_of(item):
                if isinstance(item, dict):
                    return float(item.get("relevance_score", 0.0))
                return float(getattr(item, "relevance_score", 0.0))

            context_for_prompt = [c for c in context if _relevance_of(c) >= low_cutoff]
            logger.debug(f"Applied rag.low_cutoff={low_cutoff}: kept {len(context_for_prompt)} / {len(context)} chunks")
            prompt_context = context_for_prompt
        except Exception as e:
            logger.error(f"Failed to apply rag.low_cutoff filter: {e}")
            prompt_context = context
        
        # 4. Build prompt with tenant system prompt + history + chunks
        logger.info("Building prompt...")
        messages = self.prompt_builder.build_user_message_with_history(
            query=message,
            context=prompt_context,
            conversation_history=conversation_history
        )
        
        logger.debug(f"Context to LLM: {context}")
        logger.debug(f"conversation_history: {conversation_history}")
        logger.debug(f"prompt messages to LLM: {messages}")
        
        # 5. Generate response via tenant LLM
        logger.info(f"Sending query to LLM ({self.llm.model_name})...")
        response_text, logprobs, usage = self.llm.send_messages(messages)
        logger.info("LLM response received.")
        
        # 6. Score confidence
        logger.info("Scoring confidence...")
        confidence_result = self.confidence_scorer.run(
            retrieval_results=prompt_context,
            llm_logprobs=logprobs
        )
        logger.info(f"Confidence score: {confidence_result.overall_confidence}")
        
        # 7. Decide: clarify or answer
        logger.info("Evaluating clarification needs...")
        clarification_question = None
        
        from src.utils.config_loader import get_config
        from src.llm.prompts import TENANT_CONTACT_FALLBACK
        from src.response_manager import is_unknown_response
        
        configured_patterns = get_config("fallback.unknown_patterns", default=[]) or []
        configured_patterns = [p.lower() for p in configured_patterns]
        if TENANT_CONTACT_FALLBACK.lower() not in configured_patterns:
            configured_patterns.append(TENANT_CONTACT_FALLBACK.lower())

        is_unknown = is_unknown_response(response_text, configured_patterns)
        
        if is_unknown:
            OUT_OF_DOMAIN_THRESHOLD = 0.1

            if confidence_result.retrieval_confidence < OUT_OF_DOMAIN_THRESHOLD:
                logger.info(
                    "LLM indicated unknown and no relevant context found for user %s "
                    "(retrieval_confidence=%s), out-of-domain question, using TENANT_CONTACT_FALLBACK",
                    user_id,
                    confidence_result.retrieval_confidence,
                )
                final_response = TENANT_CONTACT_FALLBACK
            elif self.clarification_manager.should_clarify(confidence_result, conversation_history):
                clarification_question = self.clarification_manager.generate_clarifying_question(
                    query=rewritten_query,
                    context=context,
                    confidence_result=confidence_result,
                    conversation_history=conversation_history
                )
                final_response = clarification_question
            else:
                logger.info("LLM indicated unknown for user %s; substituting TENANT_CONTACT_FALLBACK", user_id)
                final_response = TENANT_CONTACT_FALLBACK
        else:
            final_response = response_text
            self.clarification_manager.reset_attempts()

        # 8. Store conversation to tenant-isolated storage
        from src.models import Message as ChatMsg
        from datetime import datetime, timezone
        
        if user_id:
            import hashlib
            if str(user_id).isdigit():
                user_id_int = int(user_id)
            else:
                user_id_int = int(hashlib.md5(str(user_id).encode()).hexdigest(), 16) % (10**8)
                
            now = datetime.now(timezone.utc)
            
            self.conversation_manager.add_message(
                ChatMsg(
                    role="user", 
                    content=message, 
                    timestamp=now, 
                    user_id=user_id_int
                ), 
                user_id_int
            )
            self.conversation_manager.add_message(
                ChatMsg(
                    role="assistant", 
                    content=final_response, 
                    timestamp=now,
                    user_id=user_id_int,
                    metadata={"type": "clarification"} if clarification_question else {}
                ), 
                user_id_int
            )
        
        # 9. Return structured result
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        sources = []
        seen = set()
        for c in context:
            title = c.metadata.get("document_name", "Unknown") if isinstance(c.metadata, dict) else getattr(c.metadata, "document_name", "Unknown")
            if title not in seen:
                seen.add(title)
                url = c.metadata.get("url", "") if isinstance(c.metadata, dict) else getattr(c.metadata, "url", "")
                sources.append({"title": title, "url": url})

        return {
            "response": final_response if not clarification_question else "",
            "confidence": confidence_result.overall_confidence,
            "sources": sources if not clarification_question else [],
            "clarification_question": clarification_question,
            "tokens": {
                "input": getattr(usage, "prompt_tokens", 0) if usage else 0,
                "output": getattr(usage, "completion_tokens", 0) if usage else 0
            },
            "execution_time_ms": execution_time_ms,
            "was_summarized": was_summarized,
            "summarized_count": summarized_count,
            "summary_text": summary_text,
        }
