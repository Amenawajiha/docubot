"""Test that all user and assistant messages are logged in JSON."""

import json
import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.chat.conversation_repository import FileConversationRepository
from src.models import ConfidenceResult, Message
from src.response_manager import ResponseManager


@pytest.mark.asyncio
async def test_user_message_logged_on_clarification():
    """Test that user message is logged when clarification is triggered."""
    
    # Create a temporary directory for conversation files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Mock the websocket
        mock_websocket = AsyncMock()
        
        # Mock config to use temp directory
        with patch("src.chat.conversation_repository.get_config") as mock_config:
            mock_config.side_effect = lambda key, default=None: {
                "conversation.storage_path": temp_dir,
                "conversation.recent_count": 10,
                "conversation.enable_summarization": False,
                "conversation.storage_threshold": 50,
                "conversation.retrieval_threshold": 10,
                "rag.low_cutoff": 0.0,
                "fallback.unknown_patterns": ["I don't know", "I'm not sure"],
            }.get(key, default)
            
            # Create response manager
            response_manager = ResponseManager(mock_websocket, is_authenticated=False)
            
            # Mock the dependencies to trigger clarification
            with patch.object(response_manager.vector_retriever, "retrieve_with_reranking") as mock_retrieve, \
                 patch.object(response_manager.llm_orchestrator, "send_messages") as mock_llm, \
                 patch.object(response_manager.confidence_scorer, "run") as mock_confidence, \
                 patch.object(response_manager.clarification_manager, "should_clarify") as mock_should_clarify, \
                 patch.object(response_manager.clarification_manager, "generate_clarifying_question") as mock_gen_clarify, \
                 patch.object(response_manager.prompt_builder, "build_user_message_with_history") as mock_prompt:
                
                # Setup mocks
                mock_retrieve.return_value = []
                mock_llm.return_value = ("I don't know the answer", [])
                mock_confidence.return_value = ConfidenceResult(
                    retrieval_confidence=0.3,
                    llm_confidence=0.2,
                    overall_confidence=0.25,
                    is_confident=False,
                    confidence_breakdown={"retrieval": 0.3, "llm": 0.2}
                )
                mock_should_clarify.return_value = True
                mock_gen_clarify.return_value = "Which U.S. city or state are you looking for the VFS office address in?"
                mock_prompt.return_value = []
                
                # User sends a query
                user_id = 12345
                user_query = "VFS office address in USA"
                
                await response_manager.handle_query(user_query, user_id)
                
                # Verify websocket was called with clarification
                mock_websocket.send_json.assert_called_once()
                call_args = mock_websocket.send_json.call_args[0][0]
                assert call_args["type"] == "clarification"
                
                # Check that conversation file exists
                conv_file = os.path.join(temp_dir, f"{user_id}.json")
                assert os.path.exists(conv_file), "Conversation file should exist"
                
                # Read and verify the conversation file
                with open(conv_file, "r", encoding="utf-8") as f:
                    messages = json.load(f)
                
                # Should have 2 messages: user query + assistant clarification
                assert len(messages) == 2, f"Expected 2 messages, got {len(messages)}"
                
                # First message should be user query
                assert messages[0]["role"] == "user"
                assert messages[0]["content"] == user_query
                assert messages[0]["user_id"] == user_id
                
                # Second message should be assistant clarification
                assert messages[1]["role"] == "assistant"
                assert messages[1]["content"] == "Which U.S. city or state are you looking for the VFS office address in?"
                assert messages[1]["user_id"] == user_id
                assert messages[1]["metadata"]["type"] == "clarification"


@pytest.mark.asyncio
async def test_user_response_to_clarification_logged():
    """Test that user's response to clarification is logged."""
    
    # Create a temporary directory for conversation files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Mock the websocket
        mock_websocket = AsyncMock()
        
        # Mock config to use temp directory
        with patch("src.chat.conversation_repository.get_config") as mock_config:
            mock_config.side_effect = lambda key, default=None: {
                "conversation.storage_path": temp_dir,
                "conversation.recent_count": 10,
                "conversation.enable_summarization": False,
                "conversation.storage_threshold": 50,
                "conversation.retrieval_threshold": 10,
                "rag.low_cutoff": 0.0,
                "fallback.unknown_patterns": ["I don't know", "I'm not sure"],
            }.get(key, default)
            
            # Create response manager
            response_manager = ResponseManager(mock_websocket, is_authenticated=False)
            
            user_id = 12345
            
            # First interaction - triggers clarification
            with patch.object(response_manager.vector_retriever, "retrieve_with_reranking") as mock_retrieve, \
                 patch.object(response_manager.llm_orchestrator, "send_messages") as mock_llm, \
                 patch.object(response_manager.confidence_scorer, "run") as mock_confidence, \
                 patch.object(response_manager.clarification_manager, "should_clarify") as mock_should_clarify, \
                 patch.object(response_manager.clarification_manager, "generate_clarifying_question") as mock_gen_clarify, \
                 patch.object(response_manager.prompt_builder, "build_user_message_with_history") as mock_prompt:
                
                mock_retrieve.return_value = []
                mock_llm.return_value = ("I don't know the answer", [])
                mock_confidence.return_value = ConfidenceResult(
                    retrieval_confidence=0.3,
                    llm_confidence=0.2,
                    overall_confidence=0.25,
                    is_confident=False,
                    confidence_breakdown={"retrieval": 0.3, "llm": 0.2}
                )
                mock_should_clarify.return_value = True
                mock_gen_clarify.return_value = "Which U.S. city or state are you looking for the VFS office address in?"
                mock_prompt.return_value = []
                
                await response_manager.handle_query("VFS office address in USA", user_id)
            
            # Second interaction - user responds to clarification
            with patch.object(response_manager.vector_retriever, "retrieve_with_reranking") as mock_retrieve, \
                 patch.object(response_manager.llm_orchestrator, "send_messages") as mock_llm, \
                 patch.object(response_manager.confidence_scorer, "run") as mock_confidence, \
                 patch.object(response_manager.clarification_manager, "should_clarify") as mock_should_clarify, \
                 patch.object(response_manager.clarification_manager, "reset_attempts") as mock_reset, \
                 patch.object(response_manager.prompt_builder, "build_user_message_with_history") as mock_prompt:
                
                mock_retrieve.return_value = []
                mock_llm.return_value = ("The VFS office in New York is located at...", [])
                mock_confidence.return_value = ConfidenceResult(
                    retrieval_confidence=0.8,
                    llm_confidence=0.9,
                    overall_confidence=0.85,
                    is_confident=True,
                    confidence_breakdown={"retrieval": 0.8, "llm": 0.9}
                )
                mock_should_clarify.return_value = False
                mock_prompt.return_value = []
                
                # User responds "New York"
                await response_manager.handle_query("New York", user_id)
                
            # Read and verify the conversation file
            conv_file = os.path.join(temp_dir, f"{user_id}.json")
            with open(conv_file, "r", encoding="utf-8") as f:
                messages = json.load(f)
            
            # Should have 4 messages:
            # 1. User: "VFS office address in USA"
            # 2. Assistant: clarification question
            # 3. User: "New York"
            # 4. Assistant: answer
            assert len(messages) == 4, f"Expected 4 messages, got {len(messages)}"
            
            # Verify sequence
            assert messages[0]["role"] == "user"
            assert messages[0]["content"] == "VFS office address in USA"
            
            assert messages[1]["role"] == "assistant"
            assert "clarification" in messages[1]["metadata"]["type"]
            
            assert messages[2]["role"] == "user"
            assert messages[2]["content"] == "New York", f"Expected 'New York', got '{messages[2]['content']}'"
            
            assert messages[3]["role"] == "assistant"
            assert "New York" in messages[3]["content"]


@pytest.mark.asyncio
async def test_regular_query_messages_logged():
    """Test that regular query messages are logged correctly."""
    
    # Create a temporary directory for conversation files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Mock the websocket
        mock_websocket = AsyncMock()
        
        # Mock config to use temp directory
        with patch("src.chat.conversation_repository.get_config") as mock_config:
            mock_config.side_effect = lambda key, default=None: {
                "conversation.storage_path": temp_dir,
                "conversation.recent_count": 10,
                "conversation.enable_summarization": False,
                "conversation.storage_threshold": 50,
                "conversation.retrieval_threshold": 10,
                "rag.low_cutoff": 0.0,
                "fallback.unknown_patterns": ["I don't know", "I'm not sure"],
            }.get(key, default)
            
            # Create response manager
            response_manager = ResponseManager(mock_websocket, is_authenticated=False)
            
            user_id = 54321
            
            # Regular query (no clarification)
            with patch.object(response_manager.vector_retriever, "retrieve_with_reranking") as mock_retrieve, \
                 patch.object(response_manager.llm_orchestrator, "send_messages") as mock_llm, \
                 patch.object(response_manager.confidence_scorer, "run") as mock_confidence, \
                 patch.object(response_manager.clarification_manager, "should_clarify") as mock_should_clarify, \
                 patch.object(response_manager.clarification_manager, "reset_attempts") as mock_reset, \
                 patch.object(response_manager.prompt_builder, "build_user_message_with_history") as mock_prompt:
                
                mock_retrieve.return_value = []
                mock_llm.return_value = ("The visa requirements are...", [])
                mock_confidence.return_value = ConfidenceResult(
                    retrieval_confidence=0.8,
                    llm_confidence=0.9,
                    overall_confidence=0.85,
                    is_confident=True,
                    confidence_breakdown={"retrieval": 0.8, "llm": 0.9}
                )
                mock_should_clarify.return_value = False
                mock_prompt.return_value = []
                
                await response_manager.handle_query("What are the visa requirements?", user_id)
            
            # Read and verify the conversation file
            conv_file = os.path.join(temp_dir, f"{user_id}.json")
            with open(conv_file, "r", encoding="utf-8") as f:
                messages = json.load(f)
            
            # Should have 2 messages: user query + assistant answer
            assert len(messages) == 2, f"Expected 2 messages, got {len(messages)}"
            
            assert messages[0]["role"] == "user"
            assert messages[0]["content"] == "What are the visa requirements?"
            
            assert messages[1]["role"] == "assistant"
            assert messages[1]["content"] == "The visa requirements are..."
