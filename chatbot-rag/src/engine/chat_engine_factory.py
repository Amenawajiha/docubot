import threading
from src.config.chatbot_config import ChatbotConfig
from src.engine.tenant_chat_engine import TenantChatEngine

class ChatEngineFactory:
    """Creates isolated ChatEngine instances per workspace:chatbot pair.
    
    Thread-safe: uses a lock to guard the shared _instances dict,
    since FastAPI runs async handlers on a thread pool.
    """
    
    _instances: dict[str, "TenantChatEngine"] = {}
    _lock: threading.Lock = threading.Lock()
    
    @classmethod
    def get_or_create(cls, config: ChatbotConfig) -> "TenantChatEngine":
        key = f"{config.workspace_id}:{config.chatbot_id}"
        
        # Fast path: read without lock
        cached = cls._instances.get(key)
        if cached and cached.config_matches(config):
            return cached
        
        # Slow path: lock and create
        with cls._lock:
            cached = cls._instances.get(key)
            if cached and cached.config_matches(config):
                return cached
            
            engine = TenantChatEngine(config)
            cls._instances[key] = engine
            return engine
    
    @classmethod
    def invalidate(cls, workspace_id: str, chatbot_id: str):
        key = f"{workspace_id}:{chatbot_id}"
        with cls._lock:
            cls._instances.pop(key, None)
