"""Prompt builder for constructing LLM prompts."""

from datetime import date
from typing import Dict, List

from src.llm.prompts import (
    CLARIFICATION_SYSTEM_INSTRUCTION,
    CLARIFICATION_USER_TEMPLATE,
    CONTACT_FALLBACK,
    QUERY_PROMPT,
    SYSTEM_PROMPT_TEMPLATE,
    TENANT_SYSTEM_PROMPT_TEMPLATE,
    TENANT_CONTACT_FALLBACK,
    TENANT_QUERY_PROMPT,
)
from src.config.chatbot_config import ChatbotConfig
from src.utils import logger


class PromptBuilder:
    """Builder for constructing prompts from context and query."""

    def format_context(self, results: List) -> str:
        """
        Format retrieval results into context string.

        Args:
            results: List of retrieval results from vector DB

        Returns:
            Formatted context string
        """
        # If no results are provided, return explicit NO_CONTEXT marker so prompts
        # can handle the "no context" case cleanly.
        if not results:
            return "NO_CONTEXT"

        context_parts = []
        for idx, result in enumerate(results, 1):
            # Extract metadata safely
            metadata = (
                result.get("metadata", {})
                if isinstance(result, dict)
                else result.metadata
            )
            content = (
                result.get("content", "")
                if isinstance(result, dict)
                else result.content
            )
            relevance_score = (
                result.get("relevance_score", 0.0)
                if isinstance(result, dict)
                else result.relevance_score
            )

            # Use actual metadata fields from our document chunks
            doc_name = metadata.get("document_name", "Unknown")
            chunk_type = metadata.get("chunk_type", "text")

            context_part = f"""
Source: {doc_name}
Type: {chunk_type}
Content: {content}

"""
            context_parts.append(context_part)

        return "\n".join(context_parts)

    def build_user_message(self, query: str, context: List) -> str:
        """
        Build user message from query and context.

        Args:
            query: User query
            context: Retrieved context chunks

        Returns:
            Formatted user message (context + query)
        """
        # Format context
        formatted_context = self.format_context(context)

        # Build user message using QUERY_PROMPT template with contact_fallback
        user_message = QUERY_PROMPT.format(
            context=formatted_context, query=query, contact_fallback=CONTACT_FALLBACK
        )

        return user_message

    def build_user_message_with_history(
        self,
        query: str,
        context: List,
        conversation_history: List[Dict[str, str]] = None,
    ) -> List[Dict[str, str]]:
        """
        Build complete message array with conversation history for LLM.

        Args:
            query: Current user query
            context: Retrieved RAG context chunks
            conversation_history: Previous conversation messages

        Returns:
            List of message dicts: [
                {"role": "system", "content": "..."},
                {"role": "user", "content": "..."},
                {"role": "assistant", "content": "..."},
                ...
                {"role": "user", "content": "<context + current query>"}
            ]
        """
        messages = []

        # 1. Add system prompt (inject current date)
        current_date = date.today().isoformat()
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            current_date=current_date, contact_fallback=CONTACT_FALLBACK
        )
        messages.append({"role": "system", "content": system_prompt})

        # 2. Add conversation history (if any)
        if conversation_history:
            messages.extend(conversation_history)

        # 3. Add current query with RAG context
        formatted_context = self.format_context(context)
        current_message = QUERY_PROMPT.format(
            context=formatted_context, query=query, contact_fallback=CONTACT_FALLBACK
        )
        messages.append({"role": "user", "content": current_message})

        return messages

    def build_clarification_messages(
        self,
        query: str,
        context: List,
        retrieval_confidence: float,
        llm_confidence: float,
        overall_confidence: float,
        conversation_history: List[Dict[str, str]] = None,
    ) -> list:
        """
        Build message structure for clarification question generation.

        Args:
            query: User query
            context: Retrieved context chunks
            retrieval_confidence: Retrieval confidence score
            llm_confidence: LLM confidence score
            overall_confidence: Overall confidence score

        Returns:
            List of message dictionaries with clarification-specific system and user messages
        """

        # Build user content with query, context, conversation history, and confidence scores
        history_text = ""
        if conversation_history:
            parts = []
            for h in conversation_history:
                role = h.get("role", "")
                content = h.get("content", "")
                parts.append(f"{role}: {content}")
            history_text = "\n".join(parts)

        clarification_prompt = CLARIFICATION_USER_TEMPLATE.format(
            query=query,
            context=self.format_context(context),
            retrieval_confidence=retrieval_confidence,
            llm_confidence=llm_confidence,
            overall_confidence=overall_confidence,
        )

        if history_text:
            logger.debug("history_text for clarification: %s", history_text)
            logger.debug("Prepending conversation history to clarification prompt...")
            # Prepend conversation history to the user prompt to give the LLM full context
            clarification_prompt = (
                f"Conversation History:\n{history_text}\n\n" + clarification_prompt
            )

        return [
            {"role": "system", "content": CLARIFICATION_SYSTEM_INSTRUCTION},
            {"role": "user", "content": clarification_prompt},
        ]

    def build_user_conversation_messages(self, user_prompt: str) -> list:
        """
        Build complete message structure for LLM API.

        Args:
            user_prompt: The user message/prompt (already formatted)

        Returns:
            List of message dictionaries with system and user messages

        Examples:
            >>> builder = PromptBuilder()
            >>> messages = builder.build_messages("What is a Schengen visa?")
            >>> # Returns: [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
        """

        # Inject current date into system prompt for one-off message paths
        current_date = date.today().isoformat()
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            current_date=current_date, contact_fallback=CONTACT_FALLBACK
        )

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

class TenantPromptBuilder(PromptBuilder):
    """Prompt builder that uses per-tenant system prompt."""
    
    def __init__(self, config: "ChatbotConfig"):
        super().__init__()
        self.system_prompt = config.system_prompt or "Provide helpful and accurate answers."
        self.company_name = config.company_name or "Company"
        self.tone_preset = config.tone_preset
    
    def build_user_message_with_history(
        self,
        query: str,
        context: List,
        conversation_history: List[Dict[str, str]] = None,
    ) -> List[Dict[str, str]]:
        messages = []
        current_date = date.today().isoformat()
        
        # Inject dynamic variables into the tenant's system prompt
        try:
            system = TENANT_SYSTEM_PROMPT_TEMPLATE.format(
                company_name=self.company_name,
                system_prompt=self.system_prompt,
                current_date=current_date,
                fallback_message=TENANT_CONTACT_FALLBACK,
            )
        except KeyError:
            # Fallback if the custom prompt doesn't map variables correctly
            system = self.system_prompt
            
        messages.append({"role": "system", "content": system})
        
        if conversation_history:
            messages.extend(conversation_history)
        
        formatted_context = self.format_context(context)
        current_message = TENANT_QUERY_PROMPT.format(
            context=formatted_context,
            query=query,
            contact_fallback=TENANT_CONTACT_FALLBACK,
        )
        messages.append({"role": "user", "content": current_message})
        return messages
    
    def build_user_message(self, query: str, context: List) -> str:
        """Override to use tenant fallback in query prompt."""
        formatted_context = self.format_context(context)
        user_message = TENANT_QUERY_PROMPT.format(
            context=formatted_context, 
            query=query, 
            contact_fallback=TENANT_CONTACT_FALLBACK
        )
        return user_message

    def build_user_conversation_messages(self, user_prompt: str) -> list:
        """Override to use tenant system prompt."""
        current_date = date.today().isoformat()
        try:
            system_prompt = TENANT_SYSTEM_PROMPT_TEMPLATE.format(
                company_name=self.company_name,
                system_prompt=self.system_prompt,
                current_date=current_date,
                fallback_message=TENANT_CONTACT_FALLBACK,
            )
        except KeyError:
            system_prompt = self.system_prompt

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    
    def build_clarification_messages(
        self,
        query: str,
        context: List,
        retrieval_confidence: float,
        llm_confidence: float,
        overall_confidence: float,
        conversation_history: List[Dict[str, str]] = None,
    ) -> list:
        """Override to use tenant system prompt in clarification messages too."""
        
        # Build base clarification prompt
        base_messages = super().build_clarification_messages(
            query=query,
            context=context,
            retrieval_confidence=retrieval_confidence,
            llm_confidence=llm_confidence,
            overall_confidence=overall_confidence,
            conversation_history=conversation_history
        )
        
        # In a more advanced implementation, we might also inject the 
        # tenant's custom system prompt rules into the clarification context,
        # but for now we follow the parent's generic clarification behavior.
        return base_messages
