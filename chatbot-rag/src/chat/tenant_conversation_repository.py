import os
from typing import List

from src.chat.conversation_repository import FileConversationRepository
from src.models import Message
from src.utils.config_loader import get_config

class TenantConversationRepository(FileConversationRepository):
    """File-based conversation repository isolated per tenant."""
    
    def __init__(self, workspace_id: str, chatbot_id: str):
        # We don't call super().__init__() because it creates the base directory.
        # We want to create a tenant-specific directory instead.
        self.workspace_id = workspace_id
        self.chatbot_id = chatbot_id
        
        base_path = get_config("conversation.storage_path", default="data/conversations")
        self.storage_path = os.path.join(base_path, f"{workspace_id}_{chatbot_id}")
        os.makedirs(self.storage_path, exist_ok=True)
        self._recent_count = get_config("conversation.recent_count", default=5)
