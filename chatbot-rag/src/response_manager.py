"""Response manager - RAG pipeline orchestrator."""

from datetime import datetime, timezone

from fastapi import WebSocket

from src.service_manager import ServiceManager
from src.utils import get_config

from .chat.conversation_manager import ConversationManager
from .chat.conversation_repository import (
    CompositeConversationRepository,
    FileConversationRepository,
)
from .llm.prompts import CONTACT_FALLBACK
from .llm.query_rewriter import QueryRewriter
from .models import ConfidenceResult, Message
from .service_manager import get_service_manager
from .utils import logger


def is_unknown_response(resp: str, patterns: list[str]) -> bool:
    """Utility to detect if LLM response indicates unknown/uncertain answer.

    Args:
        resp: The LLM response string
        patterns: List of lowercase or mixed-case patterns to match

    Returns:
        True if response is empty or contains any of the patterns (case-insensitive)
    """
    if not resp:
        return True
    lowered = resp.lower()
    for p in patterns:
        if p and p.lower() in lowered:
            return True
    return False


class ResponseManager:
    """
    RAG Pipeline Orchestrator using Facade Pattern.

    Simplifies complex interactions between multiple subsystems:
    - VectorRetriever: Fetch relevant chunks
    - LLMOrchestrator: Generate responses
    - ConfidenceScorer: Evaluate answer quality
    - ClarificationManager: Handle clarifying questions
    - ConversationManager: Store conversation history
    - WebSocket: Send responses to user
    """

    def __init__(self, fe_websocket: WebSocket, is_authenticated: bool = False):
        """
        Initialize response manager with shared services.

        Args:
            websocket: WebSocket connection for sending responses
            is_authenticated: Whether the user is authenticated via JWT
        """
        self.fe_websocket = fe_websocket

        # Get shared service instances (already initialized at startup)
        service_manager: ServiceManager = get_service_manager()
        self.vector_retriever = service_manager.get_vector_retriever()
        self.llm_orchestrator = service_manager.get_llm_orchestrator()
        self.confidence_scorer = service_manager.get_confidence_scorer()
        self.prompt_builder = service_manager.get_prompt_builder()
        self.clarification_manager = service_manager.get_clarification_manager()

        # Instantiate repository classes (previously the class object was passed,
        # causing unbound method calls and missing `self` errors)
        repository_instance = (
            CompositeConversationRepository()
            if is_authenticated
            else FileConversationRepository()
        )
        logger.debug("Using repository: %s", type(repository_instance).__name__)

        self.conversation_manager = ConversationManager(repository=repository_instance)
        
        # Initialize query rewriter for context-aware query expansion
        context_window_size = get_config("conversation.context_window_size", default=5)
        self.query_rewriter = QueryRewriter(context_window_size=context_window_size)

    async def handle_query(self, query: str, user_id: int) -> None:
        """
        Orchestrates the entire RAG pipeline:
        1. Get conversation history for context
        2. Retrieve context from vector DB
        3. Generate response using LLM with history
        4. Evaluate confidence
        5. Decide whether to clarify or answer
        6. Save conversation

        Args:
            user_id: User identifier (required)
            query: User query
        """
        # 1. Get current conversation history for context
        conversation_history = self.conversation_manager.get_messages_for_llm(user_id)
        logger.debug(
            "Retrieved %s messages for user %s",
            len(conversation_history),
            user_id,
        )
        # Log the incoming user query and short conversation context
        logger.info("Incoming user query for user %s: %s", user_id, query)
        logger.debug("Conversation history length: %s", len(conversation_history))
        if conversation_history:
            logger.debug("Last message: %s", conversation_history[-1])
        
        # 1a. Rewrite query if it's ambiguous and needs context from history
        rewritten_query = self.query_rewriter.rewrite_query(query, conversation_history)
        if rewritten_query != query:
            logger.info("Using rewritten query for retrieval: %s", rewritten_query)
            # Use rewritten query for retrieval, but keep original for display/storage
            query_for_retrieval = rewritten_query
        else:
            query_for_retrieval = query

        # 2. Retrieve context from vector DB using the rewritten query
        context = self.vector_retriever.retrieve_with_reranking(query_for_retrieval, initial_k=10)

        # Log retrieved context and relevance scores (truncate content for logs)
        context_log = []
        for c in context:
            src = None
            if getattr(c, "metadata", None):
                try:
                    src = c.metadata.get("source")
                except Exception:
                    src = c.metadata
            content_preview = None
            if getattr(c, "content", None):
                content_preview = (
                    c.content if len(c.content) <= 200 else c.content[:200] + "..."
                )
            context_log.append(
                {
                    "content": content_preview,
                    "source": src,
                    "relevance": getattr(c, "relevance_score", None),
                }
            )
        logger.debug("Retrieved context for query '%s': %s", query, context_log)
        logger.debug(
            "Context relevance scores: %s",
            [getattr(c, "relevance_score", None) for c in context],
        )

        # Apply low-cutoff filter for prompt construction while preserving original
        # 'context' list for confidence scoring. This drops extremely low-relevance
        # chunks (e.g., noise) from the prompt to reduce hallucinations.
        try:
            low_cutoff = float(get_config("rag.low_cutoff"))
        except Exception:
            low_cutoff = 0.0

        try:

            def _relevance_of(item):
                # Support both object-like and dict-like retrieval results
                if isinstance(item, dict):
                    return float(item.get("relevance_score"))
                return float(getattr(item, "relevance_score"))

            context_for_prompt = [c for c in context if _relevance_of(c) >= low_cutoff]
            logger.debug(
                "Applied rag.low_cutoff=%s: kept %d / %d chunks",
                low_cutoff,
                len(context_for_prompt),
                len(context),
            )
            context = context_for_prompt
        except (AttributeError, TypeError, ValueError) as e:
            logger.exception(
                "Failed to apply rag.low_cutoff filter; using full context for prompt: %s",
                e,
            )

        # 3. Generate response (LLM can use filtered context OR its own knowledge)
        prompt = self.prompt_builder.build_user_message_with_history(
            query=query,
            context=context,
            conversation_history=conversation_history,
        )

        logger.debug("Context to LLM: %s", context)
        logger.debug("conversation_history: %s", conversation_history)
        logger.debug("prompt messages to LLM: %s", prompt)
        response, logprobs = self.llm_orchestrator.send_messages(prompt)

        
        # 4. Evaluate confidence
        confidence_result: ConfidenceResult = self.confidence_scorer.run(
            retrieval_results=context,
            llm_logprobs=logprobs,
        )

        # Log confidence breakdown if available
        logger.debug(
            "Confidence scores for user %s: retrieval=%s, llm=%s, overall=%s",
            user_id,
            confidence_result.retrieval_confidence,
            confidence_result.llm_confidence,
            confidence_result.overall_confidence,
        )

        # 5. Decide: clarify or answer?
        # Determine if LLM signaled it does not know the answer (semantic detection)
        configured_patterns = get_config("fallback.unknown_patterns", default=[]) or []
        # ensure we always catch the exact CONTACT_FALLBACK phrase
        configured_patterns = [p.lower() for p in configured_patterns]
        if CONTACT_FALLBACK.lower() not in configured_patterns:
            configured_patterns.append(CONTACT_FALLBACK.lower())

        is_unknown = is_unknown_response(response, configured_patterns)

        # If LLM indicates it doesn't know, prefer to ask a clarifying question when
        # confidence is low and attempts remain. Otherwise substitute the branded
        # CONTACT_FALLBACK so users receive helpful contact info instead of "I don't know".
        if is_unknown:
            if self.clarification_manager.should_clarify(
                confidence_result, conversation_history
            ):
                # Save the original user message before asking clarification so it's
                # persisted in conversation history even if we return early.
                user_msg = Message(
                    content=query,
                    role="user",
                    timestamp=datetime.now(timezone.utc),
                    user_id=user_id,
                    metadata={},
                )
                self.conversation_manager.add_message(user_msg, user_id)

                # Generate and send clarifying question
                clarifying_question = (
                    self.clarification_manager.generate_clarifying_question(
                        query, context, confidence_result, conversation_history
                    )
                )

                # Log the generated clarifying question
                logger.info(
                    "Generated clarifying question for user %s: %s",
                    user_id,
                    clarifying_question,
                )

                await self.fe_websocket.send_json(
                    {"type": "clarification", "content": clarifying_question}
                )

                # Save the clarification interaction
                clarification_msg = Message(
                    content=clarifying_question,
                    role="assistant",
                    timestamp=datetime.now(timezone.utc),
                    user_id=user_id,
                    metadata={"type": "clarification"},
                )
                self.conversation_manager.add_message(clarification_msg, user_id)
                return
            else:
                # Replace unknown answers with the fallback contact information
                logger.info(
                    "LLM indicated unknown for user %s; substituting CONTACT_FALLBACK",
                    user_id,
                )
                response = CONTACT_FALLBACK

        # 6. Send Answer
        logger.info(
            "Final response sent to user %s (truncated): %s",
            user_id,
            (
                response
                if not response or len(response) <= 1000
                else response[:1000] + "..."
            ),
        )
        await self.fe_websocket.send_json({"type": "answer", "content": response})

        # Reset clarification attempts on successful answer
        self.clarification_manager.reset_attempts()

        # 7. Save Answer
        # Save user message
        user_msg = Message(
            content=query,
            role="user",
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            metadata={"interaction_type": "chat_message"},
        )
        # Log before persisting user message
        logger.debug(
            "Saving user message for user %s: %s",
            user_id,
            (
                user_msg.content
                if not user_msg.content or len(user_msg.content) <= 500
                else user_msg.content[:500] + "..."
            ),
        )
        self.conversation_manager.add_message(user_msg, user_id)

        # Save assistant message
        assistant_msg = Message(
            content=response,
            role="assistant",
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            metadata={
                "interaction_type": "rag_response",
                "confidence": confidence_result.overall_confidence,
                "retrieval_confidence": confidence_result.retrieval_confidence,
                "llm_confidence": confidence_result.llm_confidence,
            },
        )
        logger.debug(
            "Saving assistant message for user %s: %s",
            user_id,
            (
                assistant_msg.content
                if not assistant_msg.content or len(assistant_msg.content) <= 500
                else assistant_msg.content[:500] + "..."
            ),
        )
        self.conversation_manager.add_message(assistant_msg, user_id)