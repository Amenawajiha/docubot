"""Configuration loader utility for loading and accessing config.yaml values."""

import json
import copy
from pathlib import Path
from typing import Any, Dict

import yaml


class ConfigLoader:
    """Config loader with support for both JSON and YAML files."""

    _instances = {}

    @classmethod
    def get_config(cls, config_path: str):
        """
        Get config from JSON file (legacy method).

        Args:
            config_path: Path to JSON config file

        Returns:
            Loaded configuration dictionary
        """
        if config_path not in cls._instances:
            with open(config_path, "r", encoding="utf-8") as f:
                cls._instances[config_path] = json.load(f)
        return cls._instances[config_path]


class YAMLConfigLoader:
    """Singleton configuration loader for YAML config file."""

    _instance = None
    _config: Dict[str, Any] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self) -> None:
        """Load configuration from config.yaml file."""
        # Find config.yaml in project root (parent of src directory)
        current_dir = Path(__file__).parent.parent.parent
        config_path = current_dir / "config.yaml"

        if not config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found at {config_path}. "
                "Please create config.yaml in the project root."
            )

        with open(config_path, "r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.

        Args:
            key: Configuration key in dot notation (e.g., 'vector.reranker_model_name')
            default: Default value if key not found

        Returns:
            Configuration value or default

        Examples:
            >>> config = YAMLConfigLoader()
            >>> config.get('vector.chroma_db_path')
            './chroma_db'
            >>> config.get('rag.retrieval_top_k')
            3
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        if isinstance(value, (dict, list)):
            return copy.deepcopy(value)
        
        return value

    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get entire configuration section.

        Args:
            section: Section name (e.g., 'vector', 'rag', 'llm')

        Returns:
            Dictionary containing all values in the section

        Examples:
            >>> config = YAMLConfigLoader()
            >>> config.get_section('vector')
            {'chroma_db_path': './chroma_db', 'collection_name': 'schengen_visa_docs', ...}
        """
        value = self._config.get(section, {})

        return copy.deepcopy(value) if isinstance(value, dict) else {}


# Create a global instance for YAML config
_yaml_config_loader = YAMLConfigLoader()


def get_config(key: str, default: Any = None) -> Any:
    """
    Get configuration value using dot notation.

    This is a convenience function that uses the global YAMLConfigLoader instance.

    Args:
        key: Configuration key in dot notation (e.g., 'vector.reranker_model_name')
        default: Default value if key not found

    Returns:
        Configuration value or default

    Examples:
        >>> from utils.config_loader import get_config
        >>> model_name = get_config('vector.reranker_model_name')
        >>> top_k = get_config('rag.retrieval_top_k', default=5)
    """
    return _yaml_config_loader.get(key, default)


def get_config_section(section: str) -> Dict[str, Any]:
    """
    Get entire configuration section.

    Args:
        section: Section name (e.g., 'vector', 'rag', 'llm')

    Returns:
        Dictionary containing all values in the section
    """
    return _yaml_config_loader.get_section(section)
