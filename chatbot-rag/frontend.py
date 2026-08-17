"""Streamlit frontend for Schengen Visa RAG Chatbot."""

import asyncio
import json
import uuid
from typing import Optional

import streamlit as st
import websockets

# Page config
st.set_page_config(
    page_title="Schengen Visa Chatbot",
    page_icon="🇪🇺",
    layout="centered",
)

# Constants
BACKEND_WS_URL = "ws://localhost:8000/ws"

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_id" not in st.session_state:
    st.session_state.user_id = f"user_{uuid.uuid4().hex[:8]}"


async def send_message_to_backend(query: str, user_id: str) -> Optional[dict]:
    """
    Send message to backend via WebSocket and get response.

    Args:
        query: User query
        user_id: User identifier

    Returns:
        Response dictionary with 'type' and 'content'
    """
    try:
        # Pass user_id in URL to prevent backend from generating new session ID
        ws_url = f"{BACKEND_WS_URL}?user_id={user_id}"
        async with websockets.connect(ws_url) as websocket:
            # Send query
            await websocket.send(json.dumps({"query": query, "user_id": user_id}))

            # Receive response
            response = await websocket.recv()
            return json.loads(response)

    except Exception as e:
        return {"type": "error", "content": f"Connection error: {str(e)}"}


def display_message(role: str, content: str, message_type: str = "answer"):
    """
    Display a chat message with appropriate styling.

    Args:
        role: 'user' or 'assistant'
        content: Message content
        message_type: 'answer', 'clarification', or 'error'
    """
    # User message
    if role == "user":
        st.chat_message("user").markdown(content)
    # Assistant messages
    else:
        if message_type == "clarification":
            st.chat_message("assistant").markdown(
                f"🤔 **Clarification needed:**\n\n{content}"
            )
        elif message_type == "error":
            st.chat_message("assistant").markdown(f"❌ **Error:**\n\n{content}")
        else:
            st.chat_message("assistant").markdown(content)


# Main UI
st.title("🇪🇺 Schengen Visa Chatbot")
st.caption(
    "Ask questions about Schengen visa requirements, applications, and procedures."
)

# Display chat history
for msg in st.session_state.messages:
    display_message(
        role=msg["role"],
        content=msg["content"],
        message_type=msg.get("message_type", "answer"),
    )

# Chat input
if prompt := st.chat_input("Ask about Schengen visas..."):
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    display_message("user", prompt)

    # Get response from backend
    with st.spinner("Thinking..."):
        response = asyncio.run(
            send_message_to_backend(prompt, st.session_state.user_id)
        )

    # Display and store assistant response
    if response:
        message_type = response.get("type", "answer")
        content = response.get("content", "No response received")

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": content,
                "message_type": message_type,
            }
        )
        display_message("assistant", content, message_type)

# Sidebar
with st.sidebar:
    st.header("Settings")
    st.session_state.user_id = st.text_input("User ID", value=st.session_state.user_id)

    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.caption(
        "💡 **Tip:** The chatbot will ask clarifying questions if your query is unclear."
    )
