"""FastAPI WebSocket routes for the chatbot application."""

import random
import time
from typing import Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import ValidationError

from src.auth.service import AuthMiddleware
from src.models import (
    Message, 
    WebSocketMessageRequest, 
    ValidatedStoredMessage,
)
from src.utils.log_helper import logger
from src.chat.conversation_repository import DatabaseConversationRepository
from src.engine.response_manager import ResponseManager

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(fe_websocket: WebSocket):
    """
    WebSocket endpoint for real-time chat communication.
    """
    await fe_websocket.accept(headers=[(b"Warning", b"299 - 'Deprecated API'")])
    token = fe_websocket.query_params.get("token")
    if token is None:
        logger.warning("Token not found in query params. Using anonymous user")
        user_id = int(time.time() * 1000) * 1000 + random.randint(0, 999)
        is_authenticated = False
    else:
        try:
            user_id = AuthMiddleware().get_current_user(token)
            is_authenticated = True
        except HTTPException as e:
            logger.error(f"Error validating token: {e}")
            await fe_websocket.send_json(
                {"type": "error", "content": "Invalid or expired token."}
            )
            await fe_websocket.close(code=1008)
            return

    response_manager = ResponseManager(fe_websocket, is_authenticated=is_authenticated)

    try:
        while True:
            incoming_data = await fe_websocket.receive_json()

            try:
                validated_request = WebSocketMessageRequest(**incoming_data)
            except ValidationError as e:
                logger.warning(f"Invalid message format from user {user_id}: {e}")
                await fe_websocket.send_json({
                    "type": "error",
                    "content": "Invalid message format. Please try again."
                })
                continue

            if validated_request.type == "store_message":
                try:
                    validated_message = ValidatedStoredMessage.from_client_payload(
                        payload=validated_request.message,
                        user_id=user_id
                    )
                    
                    message = Message(
                        content=validated_message.content,
                        role=validated_message.role,
                        timestamp=validated_message.timestamp,
                        user_id=validated_message.user_id,
                        metadata=validated_message.metadata
                    )

                    response_manager.conversation_manager.add_message(message, user_id)
                    interaction_type = message.metadata.get('interaction_type', 'message')
                    logger.debug(f"Stored {interaction_type} for user {user_id}")
                    
                except ValidationError as e:
                    logger.error(f"Message validation error: {e}")
                    await fe_websocket.send_json(
                        {"type": "error", "content": "Invalid message data"}
                    )
                except Exception as e:
                    logger.error(f"Error storing message: {e}")
                    await fe_websocket.send_json(
                        {"type": "error", "content": "Failed to store message"}
                    )
                
                continue

            query = validated_request.query

            if not query:
                await fe_websocket.send_json(
                    {"type": "error", "content": "Query cannot be empty"}
                )
                continue

            await response_manager.handle_query(query, user_id)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user: %s", user_id)
        try:
            if is_authenticated:
                summary_message = (
                    response_manager.conversation_manager.generate_summary_message(
                        user_id
                    )
                )
                if summary_message:
                    DatabaseConversationRepository().save_summary(
                        user_id,
                        summary_message=summary_message,
                    )
        except Exception as e:
            logger.error(f"Error saving session summary on disconnect: {e}")
    except Exception as e:
        logger.exception(f"Error in WebSocket connection: {str(e)}")
        try:
            if is_authenticated:
                summary_message = (
                    response_manager.conversation_manager.generate_summary_message(
                        user_id
                    )
                )
                if summary_message:
                    DatabaseConversationRepository().save_summary(
                        user_id,
                        summary_message=summary_message,
                    )
        except Exception as e:
            logger.exception("Error saving session summary on disconnect: %s", e)
            await fe_websocket.send_json(
                {
                    "type": "error",
                    "content": f"An error occurred: Please try again later.",
                }
            )

@router.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "healthy", "service": "Schengen Visa RAG Chatbot"}

@router.get("/")
async def root() -> Dict[str, str]:
    return {
        "message": "Schengen Visa RAG Chatbot API",
        "websocket": "/ws?user_id=<your_user_id>",
        "health": "/health",
    }
