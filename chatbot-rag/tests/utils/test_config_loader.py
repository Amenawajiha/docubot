"""
Comprehensive unit tests for ConfigLoader and YAMLConfigLoader.

This test suite covers:
- ConfigLoader JSON loading (legacy)
- YAMLConfigLoader singleton pattern
- Configuration loading from YAML
- Get configuration with dot notation
- Get configuration sections
- Convenience functions (get_config, get_config_section)
- Edge cases and error handling
- File not found scenarios
- Invalid configuration data
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest
import yaml

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.utils.config_loader import (
    ConfigLoader,
    YAMLConfigLoader,
    get_config,
    get_config_section,
)


# ============================================================================
# FIXTURES - Reusable Test Data and Mocks
# ============================================================================


@pytest.fixture
def sample_json_config():
    """Sample JSON configuration data."""
    return {
        "database": {
            "host": "localhost",
            "port": 5432,
            "name": "testdb"
        },
        "api": {
            "url": "https://api.example.com",
            "timeout": 30
        }
    }


@pytest.fixture
def sample_yaml_config():
    """Sample YAML configuration data."""
    return {
        "vector": {
            "chroma_db_path": "./chroma_db",
            "collection_name": "schengen_visa_docs",
            "embedding_model": "all-MiniLM-L6-v2",
            "reranker_model_name": "cross-encoder/ms-marco-MiniLM-L-6-v2"
        },
        "rag": {
            "retrieval_top_k": 3,
            "reranker_top_k": 2,
            "chunk_size": 500,
            "chunk_overlap": 50
        },
        "llm": {
            "model_name": "llama-3.1-8b-instant",
            "base_url": "https://api.groq.com/openai/v1",
            "temperature": 0.7,
            "max_tokens": 1024
        },
        "confidence": {
            "threshold": 0.6,
            "retrieval_weight": 0.4,
            "llm_weight": 0.6
        }
    }


@pytest.fixture
def mock_logger():
    """Mock logger to avoid actual logging during tests."""
    with patch("src.utils.config_loader.logger") as mock:
        yield mock


@pytest.fixture
def reset_config_loader():
    """Reset ConfigLoader singleton state between tests."""
    ConfigLoader._instances = {}
    yield
    ConfigLoader._instances = {}


@pytest.fixture
def reset_yaml_config_loader():
    """Reset YAMLConfigLoader singleton state between tests."""
    YAMLConfigLoader._instance = None
    YAMLConfigLoader._config = None
    yield
    YAMLConfigLoader._instance = None
    YAMLConfigLoader._config = None


@pytest.fixture
def reset_global_yaml_loader(sample_yaml_config):
    """
    Reset the global _yaml_config_loader instance.
    
    This is crucial for convenience function tests because _yaml_config_loader
    is created at module import time.
    """
    import src.utils.config_loader as config_module
    
    # Reset singleton state
    YAMLConfigLoader._instance = None
    YAMLConfigLoader._config = None
    
    # Mock the loader creation when module is imported
    yaml_content = yaml.dump(sample_yaml_config)
    
    with patch("builtins.open", mock_open(read_data=yaml_content)):
        with patch.object(Path, "exists", return_value=True):
            # Create new global instance
            config_module._yaml_config_loader = YAMLConfigLoader()
    
    yield config_module._yaml_config_loader
    
    # Cleanup
    YAMLConfigLoader._instance = None
    YAMLConfigLoader._config = None


# ============================================================================
# TEST CLASS: ConfigLoader (JSON) Tests
# ============================================================================


class TestConfigLoaderJSON:
    """Test ConfigLoader JSON functionality."""
    
    def test_get_config_loads_json_file(
        self, reset_config_loader, sample_json_config
    ):
        """
        Test that get_config loads JSON file.
        
        Testing Concept: Test file loading
        """
        config_path = "test_config.json"
        json_content = json.dumps(sample_json_config)
        
        with patch("builtins.open", mock_open(read_data=json_content)):
            result = ConfigLoader.get_config(config_path)
            
            assert result == sample_json_config
            assert result["database"]["host"] == "localhost"
            assert result["api"]["timeout"] == 30
    
    def test_get_config_caches_loaded_config(
        self, reset_config_loader, sample_json_config
    ):
        """
        Test that config is cached after first load.
        
        Testing Concept: Test singleton/caching behavior
        """
        config_path = "test_config.json"
        json_content = json.dumps(sample_json_config)
        
        mock_file = mock_open(read_data=json_content)
        
        with patch("builtins.open", mock_file):
            # First call
            result1 = ConfigLoader.get_config(config_path)
            
            # Second call
            result2 = ConfigLoader.get_config(config_path)
            
            # File should only be opened once
            assert mock_file.call_count == 1
            
            # Both results should be the same
            assert result1 == result2
            assert result1 is result2  # Same object
    
    def test_get_config_loads_multiple_files(
        self, reset_config_loader, sample_json_config
    ):
        """
        Test that multiple config files can be loaded.
        
        Testing Concept: Test multiple instances
        """
        config1_path = "config1.json"
        config2_path = "config2.json"
        
        config1_data = {"key1": "value1"}
        config2_data = {"key2": "value2"}
        
        def mock_open_multiple(path, *args, **kwargs):
            if config1_path in str(path):
                return mock_open(read_data=json.dumps(config1_data))()
            elif config2_path in str(path):
                return mock_open(read_data=json.dumps(config2_data))()
        
        with patch("builtins.open", side_effect=mock_open_multiple):
            result1 = ConfigLoader.get_config(config1_path)
            result2 = ConfigLoader.get_config(config2_path)
            
            assert result1 == config1_data
            assert result2 == config2_data
            assert result1 != result2
    
    def test_get_config_raises_file_not_found(self, reset_config_loader):
        """
        Test that FileNotFoundError is raised for missing file.
        
        Testing Concept: Test file not found error
        """
        with patch("builtins.open", side_effect=FileNotFoundError):
            with pytest.raises(FileNotFoundError):
                ConfigLoader.get_config("missing_config.json")
    
    def test_get_config_raises_json_decode_error(self, reset_config_loader):
        """
        Test that JSONDecodeError is raised for invalid JSON.
        
        Testing Concept: Test invalid data format
        """
        invalid_json = "{ invalid json }"
        
        with patch("builtins.open", mock_open(read_data=invalid_json)):
            with pytest.raises(json.JSONDecodeError):
                ConfigLoader.get_config("invalid.json")
    
    def test_get_config_with_empty_json(self, reset_config_loader):
        """
        Test loading empty JSON object.
        
        Testing Concept: Test empty input
        """
        empty_json = "{}"
        
        with patch("builtins.open", mock_open(read_data=empty_json)):
            result = ConfigLoader.get_config("empty.json")
            
            assert result == {}
    
    def test_get_config_with_nested_json(self, reset_config_loader):
        """
        Test loading deeply nested JSON structure.
        
        Testing Concept: Test complex nested data
        """
        nested_config = {
            "level1": {
                "level2": {
                    "level3": {
                        "value": "deep"
                    }
                }
            }
        }
        
        json_content = json.dumps(nested_config)
        
        with patch("builtins.open", mock_open(read_data=json_content)):
            result = ConfigLoader.get_config("nested.json")
            
            assert result["level1"]["level2"]["level3"]["value"] == "deep"
    
    def test_get_config_with_array_in_json(self, reset_config_loader):
        """
        Test loading JSON with arrays.
        
        Testing Concept: Test array handling
        """
        config_with_arrays = {
            "services": ["service1", "service2", "service3"],
            "ports": [8080, 8081, 8082]
        }
        
        json_content = json.dumps(config_with_arrays)
        
        with patch("builtins.open", mock_open(read_data=json_content)):
            result = ConfigLoader.get_config("array.json")
            
            assert result["services"] == ["service1", "service2", "service3"]
            assert result["ports"] == [8080, 8081, 8082]
    
    def test_get_config_with_boolean_values(self, reset_config_loader):
        """
        Test loading JSON with boolean values.
        
        Testing Concept: Test boolean type
        """
        config_with_bools = {
            "enabled": True,
            "debug": False
        }
        
        json_content = json.dumps(config_with_bools)
        
        with patch("builtins.open", mock_open(read_data=json_content)):
            result = ConfigLoader.get_config("bool.json")
            
            assert result["enabled"] is True
            assert result["debug"] is False
    
    def test_get_config_with_null_values(self, reset_config_loader):
        """
        Test loading JSON with null values.
        
        Testing Concept: Test null handling
        """
        config_with_nulls = {
            "optional_value": None,
            "required_value": "present"
        }
        
        json_content = json.dumps(config_with_nulls)
        
        with patch("builtins.open", mock_open(read_data=json_content)):
            result = ConfigLoader.get_config("null.json")
            
            assert result["optional_value"] is None
            assert result["required_value"] == "present"


# ============================================================================
# TEST CLASS: YAMLConfigLoader Initialization
# ============================================================================


class TestYAMLConfigLoaderInitialization:
    """Test YAMLConfigLoader initialization and singleton pattern."""
    
    def test_yaml_config_loader_is_singleton(
        self, reset_yaml_config_loader, sample_yaml_config
    ):
        """
        Test that YAMLConfigLoader follows singleton pattern.
        
        Testing Concept: Test singleton pattern
        """
        yaml_content = yaml.dump(sample_yaml_config)
        
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            with patch.object(Path, "exists", return_value=True):
                loader1 = YAMLConfigLoader()
                loader2 = YAMLConfigLoader()
                
                assert loader1 is loader2
    
    def test_yaml_config_loader_loads_config_on_first_instantiation(
        self, reset_yaml_config_loader, sample_yaml_config
    ):
        """
        Test that config is loaded on first instantiation.
        
        Testing Concept: Test lazy loading
        """
        yaml_content = yaml.dump(sample_yaml_config)
        mock_file = mock_open(read_data=yaml_content)
        
        with patch("builtins.open", mock_file):
            with patch.object(Path, "exists", return_value=True):
                loader = YAMLConfigLoader()
                
                # Config should be loaded
                assert loader._config is not None
                assert loader._config == sample_yaml_config
    
    def test_yaml_config_loader_only_loads_once(
        self, reset_yaml_config_loader, sample_yaml_config
    ):
        """
        Test that config is only loaded once even with multiple instances.
        
        Testing Concept: Test singleton loading
        """
        yaml_content = yaml.dump(sample_yaml_config)
        mock_file = mock_open(read_data=yaml_content)
        
        with patch("builtins.open", mock_file):
            with patch.object(Path, "exists", return_value=True):
                loader1 = YAMLConfigLoader()
                loader2 = YAMLConfigLoader()
                loader3 = YAMLConfigLoader()
                
                # File should only be opened once
                assert mock_file.call_count == 1
    
    def test_yaml_config_loader_raises_file_not_found(
        self, reset_yaml_config_loader
    ):
        """
        Test that FileNotFoundError is raised when config.yaml doesn't exist.
        
        Testing Concept: Test file not found error
        """
        with patch.object(Path, "exists", return_value=False):
            with pytest.raises(FileNotFoundError, match="Configuration file not found"):
                YAMLConfigLoader()
    
    def test_yaml_config_loader_finds_config_in_project_root(
        self, reset_yaml_config_loader, sample_yaml_config
    ):
        """
        Test that config.yaml is searched in project root.
        
        Testing Concept: Test file path resolution
        """
        yaml_content = yaml.dump(sample_yaml_config)
        
        with patch("builtins.open", mock_open(read_data=yaml_content)) as mock_file:
            with patch.object(Path, "exists", return_value=True):
                loader = YAMLConfigLoader()
                
                # Verify file was opened
                mock_file.assert_called_once()
                
                # Verify path contains config.yaml
                call_args = mock_file.call_args[0]
                assert "config.yaml" in str(call_args[0])
    
    def test_yaml_config_loader_creates_config_path_correctly(
        self, reset_yaml_config_loader, sample_yaml_config
    ):
        """
        Test that config path is constructed correctly relative to file location.
        
        Testing Concept: Test path construction
        """
        yaml_content = yaml.dump(sample_yaml_config)
        
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            with patch.object(Path, "exists", return_value=True) as mock_exists:
                YAMLConfigLoader()
                
                # Verify exists was called
                mock_exists.assert_called_once()


# ============================================================================
# TEST CLASS: YAMLConfigLoader Get Method
# ============================================================================


class TestYAMLConfigLoaderGet:
    """Test YAMLConfigLoader.get() method."""
    
    def test_get_returns_value_with_dot_notation(
        self, reset_yaml_config_loader, sample_yaml_config
    ):
        """
        Test getting value using dot notation.
        
        Testing Concept: Test dot notation access
        """
        yaml_content = yaml.dump(sample_yaml_config)
        
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            with patch.object(Path, "exists", return_value=True):
                loader = YAMLConfigLoader()
                
                result = loader.get("vector.chroma_db_path")
                
                assert result == "./chroma_db"
    
    def test_get_returns_nested_value(
        self, reset_yaml_config_loader, sample_yaml_config
    ):
        """
        Test getting nested configuration value.
        
        Testing Concept: Test nested access
        """
        yaml_content = yaml.dump(sample_yaml_config)
        
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            with patch.object(Path, "exists", return_value=True):
                loader = YAMLConfigLoader()
                
                result = loader.get("rag.retrieval_top_k")
                
                assert result == 3
    
    def test_get_returns_top_level_value(
        self, reset_yaml_config_loader, sample_yaml_config
    ):
        """
        Test getting top-level configuration section.
        
        Testing Concept: Test single key access
        """
        yaml_content = yaml.dump(sample_yaml_config)
        
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            with patch.object(Path, "exists", return_value=True):
                loader = YAMLConfigLoader()
                
                result = loader.get("vector")
                
                assert isinstance(result, dict)
                assert result["chroma_db_path"] == "./chroma_db"
    
    def test_get_returns_default_for_missing_key(
        self, reset_yaml_config_loader, sample_yaml_config
    ):
        """
        Test that default value is returned for missing key.
        
        Testing Concept: Test default parameter
        """
        yaml_content = yaml.dump(sample_yaml_config)
        
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            with patch.object(Path, "exists", return_value=True):
                loader = YAMLConfigLoader()
                
                result = loader.get("nonexistent.key", default="default_value")
                
                assert result == "default_value"
    
    def test_get_returns_none_for_missing_key_without_default(
        self, reset_yaml_config_loader, sample_yaml_config
    ):
        """
        Test that None is returned for missing key without default.
        
        Testing Concept: Test None default
        """
        yaml_content = yaml.dump(sample_yaml_config)
        
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            with patch.object(Path, "exists", return_value=True):
                loader = YAMLConfigLoader()
                
                result = loader.get("nonexistent.key")
                
                assert result is None
    
    def test_get_returns_default_for_partial_path(
        self, reset_yaml_config_loader, sample_yaml_config
    ):
        """
        Test that default is returned when partial path doesn't exist.
        
        Testing Concept: Test partial path miss
        """
        yaml_content = yaml.dump(sample_yaml_config)
        
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            with patch.object(Path, "exists", return_value=True):
                loader = YAMLConfigLoader()
                
                result = loader.get("vector.nonexistent.key", default="default")
                
                assert result == "default"
    
    def test_get_handles_empty_string_key(
        self, reset_yaml_config_loader, sample_yaml_config
    ):
        """
        Test handling of empty string key.
        
        Testing Concept: Test empty input
        """
        yaml_content = yaml.dump(sample_yaml_config)
        
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            with patch.object(Path, "exists", return_value=True):
                loader = YAMLConfigLoader()
                
                result = loader.get("", default="default")
                
                # Empty string splits to [''], which should miss
                assert result == "default"
    
    def test_get_with_numeric_value(
        self, reset_yaml_config_loader, sample_yaml_config
    ):
        """
        Test getting numeric configuration value.
        
        Testing Concept: Test different data types
        """
        yaml_content = yaml.dump(sample_yaml_config)
        
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            with patch.object(Path, "exists", return_value=True):
                loader = YAMLConfigLoader()
                
                result = loader.get("llm.temperature")
                
                assert result == 0.7
                assert isinstance(result, float)
    
    def test_get_with_string_value(
        self, reset_yaml_config_loader, sample_yaml_config
    ):
        """
        Test getting string configuration value.
        
        Testing Concept: Test string type
        """
        yaml_content = yaml.dump(sample_yaml_config)
        
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            with patch.object(Path, "exists", return_value=True):
                loader = YAMLConfigLoader()
                
                result = loader.get("llm.model_name")
                
                assert result == "llama-3.1-8b-instant"
                assert isinstance(result, str)
    
    def test_get_with_deeply_nested_path(
        self, reset_yaml_config_loader
    ):
        """
        Test getting value from deeply nested path.
        
        Testing Concept: Test deep nesting
        """
        deep_config = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "value": "deep_value"
                        }
                    }
                }
            }
        }
        
        yaml_content = yaml.dump(deep_config)
        
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            with patch.object(Path, "exists", return_value=True):
                loader = YAMLConfigLoader()
                
                result = loader.get("level1.level2.level3.level4.value")
                
                assert result == "deep_value"
    
    def test_get_with_single_dot_in_key(
        self, reset_yaml_config_loader, sample_yaml_config
    ):
        """
        Test getting value with single level dot notation.
        
        Testing Concept: Test minimal dot notation
        """
        yaml_content = yaml.dump(sample_yaml_config)
        
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            with patch.object(Path, "exists", return_value=True):
                loader = YAMLConfigLoader()
                
                result = loader.get("vector.embedding_model")
                
                assert result == "all-MiniLM-L6-v2"
    
    def test_get_with_integer_value(
        self, reset_yaml_config_loader, sample_yaml_config
    ):
        """
        Test getting integer configuration value.
        
        Testing Concept: Test integer type
        """
        yaml_content = yaml.dump(sample_yaml_config)
        
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            with patch.object(Path, "exists", return_value=True):
                loader = YAMLConfigLoader()
                
                result = loader.get("llm.max_tokens")
                
                assert result == 1024
                assert isinstance(result, int)


# ============================================================================
# TEST CLASS: YAMLConfigLoader Get Section
# ============================================================================


class TestYAMLConfigLoaderGetSection:
    """Test YAMLConfigLoader.get_section() method."""
    
    def test_get_section_returns_entire_section(
        self, reset_yaml_config_loader, sample_yaml_config
    ):
        """
        Test getting entire configuration section.
        
        Testing Concept: Test section retrieval
        """
        yaml_content = yaml.dump(sample_yaml_config)
        
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            with patch.object(Path, "exists", return_value=True):
                loader = YAMLConfigLoader()
                
                result = loader.get_section("vector")
                
                assert isinstance(result, dict)
                assert result == sample_yaml_config["vector"]
                assert "chroma_db_path" in result
                assert "embedding_model" in result
    
    def test_get_section_returns_empty_dict_for_missing_section(
        self, reset_yaml_config_loader, sample_yaml_config
    ):
        """
        Test that empty dict is returned for missing section.
        
        Testing Concept: Test missing section
        """
        yaml_content = yaml.dump(sample_yaml_config)
        
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            with patch.object(Path, "exists", return_value=True):
                loader = YAMLConfigLoader()
                
                result = loader.get_section("nonexistent")
                
                assert result == {}
    
    def test_get_section_returns_all_nested_values(
        self, reset_yaml_config_loader, sample_yaml_config
    ):
        """
        Test that all nested values in section are returned.
        
        Testing Concept: Test complete section data
        """
        yaml_content = yaml.dump(sample_yaml_config)
        
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            with patch.object(Path, "exists", return_value=True):
                loader = YAMLConfigLoader()
                
                result = loader.get_section("llm")
                
                assert result["model_name"] == "llama-3.1-8b-instant"
                assert result["temperature"] == 0.7
                assert result["max_tokens"] == 1024
    
    def test_get_section_with_empty_string(
        self, reset_yaml_config_loader, sample_yaml_config
    ):
        """
        Test get_section with empty string.
        
        Testing Concept: Test empty input
        """
        yaml_content = yaml.dump(sample_yaml_config)
        
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            with patch.object(Path, "exists", return_value=True):
                loader = YAMLConfigLoader()
                
                result = loader.get_section("")
                
                assert result == {}
    
    def test_get_section_does_not_modify_original_config(
        self, reset_yaml_config_loader, sample_yaml_config
    ):
        """
        Test that get_section doesn't modify the original config.
        
        Testing Concept: Test data immutability
        """
        yaml_content = yaml.dump(sample_yaml_config)
        
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            with patch.object(Path, "exists", return_value=True):
                loader = YAMLConfigLoader()
                
                result = loader.get_section("vector")
                result["new_key"] = "new_value"
                
                # Get section again
                result2 = loader.get_section("vector")
                
                # Original should not have the new key
                assert "new_key" not in result2


# ============================================================================
# TEST CLASS: Convenience Functions
# ============================================================================


class TestConvenienceFunctions:
    """Test get_config() and get_config_section() convenience functions."""
    
    def test_get_config_function_uses_global_loader(
        self, reset_global_yaml_loader, sample_yaml_config
    ):
        """
        Test that get_config() uses global loader instance.
        
        Testing Concept: Test global function
        """
        result = get_config("vector.chroma_db_path")
        
        assert result == "./chroma_db"
    
    def test_get_config_function_with_default(
        self, reset_global_yaml_loader, sample_yaml_config
    ):
        """
        Test get_config() with default parameter.
        
        Testing Concept: Test default parameter
        """
        result = get_config("nonexistent.key", default="my_default")
        
        assert result == "my_default"
    
    def test_get_config_section_function_uses_global_loader(
        self, reset_global_yaml_loader, sample_yaml_config
    ):
        """
        Test that get_config_section() uses global loader instance.
        
        Testing Concept: Test global function
        """
        result = get_config_section("rag")
        
        assert isinstance(result, dict)
        assert result == sample_yaml_config["rag"]
    
    def test_get_config_section_function_returns_empty_dict(
        self, reset_global_yaml_loader, sample_yaml_config
    ):
        """
        Test that get_config_section() returns empty dict for missing section.
        
        Testing Concept: Test missing section handling
        """
        result = get_config_section("nonexistent")
        
        assert result == {}
    
    def test_multiple_get_config_calls_use_same_instance(
        self, reset_global_yaml_loader, sample_yaml_config
    ):
        """
        Test that multiple calls use the same loader instance.
        
        Testing Concept: Test singleton usage
        """
        result1 = get_config("vector.chroma_db_path")
        result2 = get_config("rag.retrieval_top_k")
        result3 = get_config_section("llm")
        
        # All calls should work
        assert result1 == "./chroma_db"
        assert result2 == 3
        assert isinstance(result3, dict)
    
    def test_get_config_function_with_none_default(
        self, reset_global_yaml_loader, sample_yaml_config
    ):
        """
        Test get_config() with None as default.
        
        Testing Concept: Test explicit None default
        """
        result = get_config("missing.key", default=None)
        
        assert result is None
    
    def test_get_config_function_returns_complex_types(
        self, reset_global_yaml_loader, sample_yaml_config
    ):
        """
        Test that get_config() can return complex types (dicts).
        
        Testing Concept: Test complex return types
        """
        result = get_config("vector")
        
        assert isinstance(result, dict)
        assert "chroma_db_path" in result


# ============================================================================
# TEST CLASS: Edge Cases and Error Handling
# ============================================================================


class TestEdgeCasesAndErrors:
    """Test edge cases and error handling."""
    
    def test_yaml_config_loader_with_invalid_yaml(
        self, reset_yaml_config_loader
    ):
        """
        Test that YAMLError is raised for invalid YAML.
        
        Testing Concept: Test invalid data format
        """
        invalid_yaml = "{ invalid: yaml: syntax: }"
        
        with patch("builtins.open", mock_open(read_data=invalid_yaml)):
            with patch.object(Path, "exists", return_value=True):
                with pytest.raises(yaml.YAMLError):
                    YAMLConfigLoader()
    
    def test_yaml_config_loader_with_empty_file(
        self, reset_yaml_config_loader
    ):
        """
        Test loading empty YAML file.
        
        Testing Concept: Test empty input
        """
        empty_yaml = ""
        
        with patch("builtins.open", mock_open(read_data=empty_yaml)):
            with patch.object(Path, "exists", return_value=True):
                loader = YAMLConfigLoader()
                
                # Empty YAML should result in None, which get() should handle
                assert loader._config is None
    
    def test_yaml_config_loader_with_list_root(
        self, reset_yaml_config_loader
    ):
        """
        Test YAML with list as root (unusual but valid).
        
        Testing Concept: Test unexpected structure
        """
        list_yaml = yaml.dump(["item1", "item2", "item3"])
        
        with patch("builtins.open", mock_open(read_data=list_yaml)):
            with patch.object(Path, "exists", return_value=True):
                loader = YAMLConfigLoader()
                
                # Config is a list, not a dict
                assert isinstance(loader._config, list)
                
                # get() should return default since it's not a dict
                result = loader.get("any.key", default="default")
                assert result == "default"
    
    def test_get_with_non_dict_intermediate_value(
        self, reset_yaml_config_loader
    ):
        """
        Test get() when intermediate value is not a dict.
        
        Testing Concept: Test type mismatch in path
        """
        config = {
            "section": {
                "value": "string_value",
                "nested": {"key": "value"}
            }
        }
        
        yaml_content = yaml.dump(config)
        
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            with patch.object(Path, "exists", return_value=True):
                loader = YAMLConfigLoader()
                
                # Try to access further into a string value
                result = loader.get("section.value.nonexistent", default="default")
                
                assert result == "default"
    
    def test_yaml_config_loader_file_permission_error(
        self, reset_yaml_config_loader
    ):
        """
        Test that PermissionError is raised for inaccessible file.
        
        Testing Concept: Test file permission error
        """
        with patch("builtins.open", side_effect=PermissionError):
            with patch.object(Path, "exists", return_value=True):
                with pytest.raises(PermissionError):
                    YAMLConfigLoader()
    
    def test_config_loader_with_unicode_content(
        self, reset_config_loader
    ):
        """
        Test ConfigLoader with unicode characters.
        
        Testing Concept: Test unicode handling
        """
        unicode_config = {
            "message": "Hello 世界 مرحبا",
            "emoji": "🎉🎊"
        }
        
        json_content = json.dumps(unicode_config, ensure_ascii=False)
        
        with patch("builtins.open", mock_open(read_data=json_content)):
            result = ConfigLoader.get_config("unicode.json")
            
            assert result["message"] == "Hello 世界 مرحبا"
            assert result["emoji"] == "🎉🎊"
    
    def test_yaml_config_loader_with_special_yaml_features(
        self, reset_yaml_config_loader
    ):
        """
        Test YAML with anchors and aliases.
        
        Testing Concept: Test YAML special features
        """
        yaml_with_anchors = """
        defaults: &defaults
          timeout: 30
          retries: 3
        
        service1:
          <<: *defaults
          name: service1
        
        service2:
          <<: *defaults
          name: service2
        """
        
        with patch("builtins.open", mock_open(read_data=yaml_with_anchors)):
            with patch.object(Path, "exists", return_value=True):
                loader = YAMLConfigLoader()
                
                result1 = loader.get("service1.timeout")
                result2 = loader.get("service2.retries")
                
                assert result1 == 30
                assert result2 == 3
    
    def test_get_config_with_none_config(
        self, reset_yaml_config_loader
    ):
        """
        Test get() when _config is None.
        
        Testing Concept: Test None config handling
        """
        empty_yaml = ""
        
        with patch("builtins.open", mock_open(read_data=empty_yaml)):
            with patch.object(Path, "exists", return_value=True):
                loader = YAMLConfigLoader()
                
                # Config should be None for empty YAML
                result = loader.get("any.key", default="default")
                
                assert result == "default"
    
    def test_get_section_with_none_config(
        self, reset_yaml_config_loader
    ):
        """
        Test get_section() when _config is None.
        
        Testing Concept: Test None config handling - should handle gracefully
        """
        empty_yaml = ""
        
        with patch("builtins.open", mock_open(read_data=empty_yaml)):
            with patch.object(Path, "exists", return_value=True):
                loader = YAMLConfigLoader()
                
                # This currently raises AttributeError - test documents actual behavior
                # The code should handle None config, but currently doesn't
                with pytest.raises(AttributeError, match="'NoneType' object has no attribute 'get'"):
                    loader.get_section("any_section")
    
    def test_yaml_config_loader_with_comments(
        self, reset_yaml_config_loader
    ):
        """
        Test YAML with comments.
        
        Testing Concept: Test YAML comment handling
        """
        yaml_with_comments = """
        # This is a comment
        vector:
          chroma_db_path: "./chroma_db"  # Path comment
          # Another comment
          collection_name: "test"
        """
        
        with patch("builtins.open", mock_open(read_data=yaml_with_comments)):
            with patch.object(Path, "exists", return_value=True):
                loader = YAMLConfigLoader()
                
                result = loader.get("vector.chroma_db_path")
                assert result == "./chroma_db"
    
    def test_yaml_config_loader_with_multiline_strings(
        self, reset_yaml_config_loader
    ):
        """
        Test YAML with multiline strings.
        
        Testing Concept: Test YAML multiline handling
        """
        yaml_multiline = """
        description: |
          This is a long
          multiline description
          that spans multiple lines
        """
        
        with patch("builtins.open", mock_open(read_data=yaml_multiline)):
            with patch.object(Path, "exists", return_value=True):
                loader = YAMLConfigLoader()
                
                result = loader.get("description")
                assert "multiline" in result
                assert "\n" in result


# ============================================================================
# TEST CLASS: Integration Tests
# ============================================================================


class TestIntegrationScenarios:
    """Test realistic usage scenarios."""
    
    def test_full_config_workflow(
        self, reset_global_yaml_loader, sample_yaml_config
    ):
        """
        Test complete configuration loading and access workflow.
        
        Testing Concept: Integration test
        """
        # Load config via global function
        chroma_path = get_config("vector.chroma_db_path")
        assert chroma_path == "./chroma_db"
        
        # Load section via global function
        rag_config = get_config_section("rag")
        assert rag_config["retrieval_top_k"] == 3
        
        # Load with default
        custom_value = get_config("custom.value", default=100)
        assert custom_value == 100
        
        # Load multiple values
        model_name = get_config("llm.model_name")
        temperature = get_config("llm.temperature")
        
        assert model_name == "llama-3.1-8b-instant"
        assert temperature == 0.7
    
    def test_accessing_all_config_sections(
        self, reset_global_yaml_loader, sample_yaml_config
    ):
        """
        Test accessing all configuration sections.
        
        Testing Concept: Test comprehensive access
        """
        vector_config = get_config_section("vector")
        rag_config = get_config_section("rag")
        llm_config = get_config_section("llm")
        confidence_config = get_config_section("confidence")
        
        assert vector_config["collection_name"] == "schengen_visa_docs"
        assert rag_config["chunk_size"] == 500
        assert llm_config["base_url"] == "https://api.groq.com/openai/v1"
        assert confidence_config["threshold"] == 0.6
    
    def test_mixed_access_patterns(
        self, reset_global_yaml_loader, sample_yaml_config
    ):
        """
        Test mixing different access patterns.
        
        Testing Concept: Test pattern mixing
        """
        # Access via dot notation
        threshold = get_config("confidence.threshold")
        
        # Access entire section
        rag_section = get_config_section("rag")
        
        # Access with default
        missing = get_config("missing.key", default="default")
        
        assert threshold == 0.6
        assert isinstance(rag_section, dict)
        assert missing == "default"


# ============================================================================
# PARAMETERIZED TESTS
# ============================================================================


class TestParameterizedScenarios:
    """Test multiple scenarios efficiently with parameterization."""
    
    @pytest.mark.parametrize("key,expected", [
        ("vector.chroma_db_path", "./chroma_db"),
        ("vector.collection_name", "schengen_visa_docs"),
        ("rag.retrieval_top_k", 3),
        ("rag.chunk_size", 500),
        ("llm.temperature", 0.7),
        ("llm.max_tokens", 1024),
        ("confidence.threshold", 0.6),
    ])
    def test_get_various_config_values(
        self, reset_global_yaml_loader, sample_yaml_config, key, expected
    ):
        """
        Test getting various configuration values.
        
        Testing Concept: Parameterized value retrieval
        """
        result = get_config(key)
        assert result == expected
    
    @pytest.mark.parametrize("section", ["vector", "rag", "llm", "confidence"])
    def test_get_various_sections(
        self, reset_global_yaml_loader, sample_yaml_config, section
    ):
        """
        Test getting various configuration sections.
        
        Testing Concept: Parameterized section retrieval
        """
        result = get_config_section(section)
        
        assert isinstance(result, dict)
        assert len(result) > 0
    
    @pytest.mark.parametrize("missing_key,default", [
        ("nonexistent.key", "default1"),
        ("missing.section.value", 999),
        ("invalid", None),
        ("x.y.z", []),
        ("a.b.c.d.e", {}),
    ])
    def test_get_missing_keys_with_defaults(
        self, reset_global_yaml_loader, sample_yaml_config, missing_key, default
    ):
        """
        Test getting missing keys with various defaults.
        
        Testing Concept: Parameterized default handling
        """
        result = get_config(missing_key, default=default)
        assert result == default
    
    @pytest.mark.parametrize("config_data,key,expected", [
        ({"simple": "value"}, "simple", "value"),
        ({"nested": {"key": "value"}}, "nested.key", "value"),
        ({"deep": {"nested": {"key": "value"}}}, "deep.nested.key", "value"),
        ({"number": 42}, "number", 42),
        ({"float": 3.14}, "float", 3.14),
        ({"bool": True}, "bool", True),
    ])
    def test_get_various_data_types(
        self, reset_yaml_config_loader, config_data, key, expected
    ):
        """
        Test getting various data types.
        
        Testing Concept: Parameterized type testing
        """
        yaml_content = yaml.dump(config_data)
        
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            with patch.object(Path, "exists", return_value=True):
                loader = YAMLConfigLoader()
                
                result = loader.get(key)
                assert result == expected


# ============================================================================
# Run tests from command line
# ============================================================================


if __name__ == "__main__":
    pytest.main([
        __file__, 
        "-v", 
        "--tb=short",
        "--cov=src.utils.config_loader",
        "--cov-report=term-missing"
    ])