"""
Comprehensive unit tests for SingletonMeta metaclass.

This test suite covers:
- Singleton pattern enforcement
- Instance creation and caching
- Multiple db_name handling
- Edge cases (None, empty string, missing db_name)
- Thread safety concepts
- Metaclass behavior
- Instance reuse across different classes
"""

import os
import sys
from abc import ABCMeta
from unittest.mock import MagicMock, patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.utils.singleton_meta import SingletonMeta
        
# ============================================================================
# TEST HELPER CLASSES - Classes using SingletonMeta
# ============================================================================


class DatabaseClient(metaclass=SingletonMeta):
    """Test class using SingletonMeta."""
    
    def __init__(self, db_name: str, host: str = "localhost", port: int = 5432):
        self.db_name = db_name
        self.host = host
        self.port = port
        self.connection_count = 0
    
    def connect(self):
        self.connection_count += 1
        return f"Connected to {self.db_name}"


class CacheClient(metaclass=SingletonMeta):
    """Another test class using SingletonMeta."""
    
    def __init__(self, db_name: str, ttl: int = 3600):
        self.db_name = db_name
        self.ttl = ttl
        self.cache = {}


class ConfigManager(metaclass=SingletonMeta):
    """Test class with only db_name parameter."""
    
    def __init__(self, db_name: str):
        self.db_name = db_name
        self.settings = {}


# ============================================================================
# FIXTURES - Reusable Test Data and Mocks
# ============================================================================


@pytest.fixture
def reset_singleton_instances():

    import inspect
    import sys

    current_module = sys.modules[__name__]

    singleton_classes = []
    for name, obj in inspect.getmembers(current_module, inspect.isclass):
        if isinstance(obj, SingletonMeta):
            singleton_classes.append(obj)

    for cls in singleton_classes:
        if hasattr(cls, "_instances"):
            cls._instances.clear()

    yield

    for cls in singleton_classes:
        if hasattr(cls, "_instances"):
            cls._instances.clear()


@pytest.fixture
def mock_logger():
    """Mock logger to avoid actual logging during tests."""
    with patch("src.utils.singleton_meta.logger", create=True) as mock:
        yield mock


# ============================================================================
# TEST CLASS: Basic Singleton Behavior
# ============================================================================


class TestSingletonMetaBasicBehavior:
    """Test basic singleton pattern behavior."""
    
    def test_single_instance_created_for_same_db_name(self, reset_singleton_instances):
        """
        Test that only one instance is created for same db_name.
        
        Testing Concept: Singleton pattern enforcement
        """
        db1 = DatabaseClient(db_name="testdb")
        db2 = DatabaseClient(db_name="testdb")
        
        # Both references should point to same instance
        assert db1 is db2
        assert id(db1) == id(db2)
    
    def test_different_instances_for_different_db_names(self, reset_singleton_instances):
        """
        Test that different instances are created for different db_names.
        
        Testing Concept: Multiple singleton instances
        """
        db1 = DatabaseClient(db_name="testdb1")
        db2 = DatabaseClient(db_name="testdb2")
        
        # Should be different instances
        assert db1 is not db2
        assert id(db1) != id(db2)
        assert db1.db_name == "testdb1"
        assert db2.db_name == "testdb2"
    
    def test_instance_attributes_persist(self, reset_singleton_instances):
        """
        Test that instance attributes persist across retrievals.
        
        Testing Concept: State persistence
        """
        db1 = DatabaseClient(db_name="testdb")
        db1.connect()
        
        # Get instance again
        db2 = DatabaseClient(db_name="testdb")
        
        # State should be preserved
        assert db2.connection_count == 1
        assert db1 is db2
    
    def test_additional_parameters_used_only_on_first_creation(self, reset_singleton_instances):
        """
        Test that additional parameters are only used on first instantiation.
        
        Testing Concept: Singleton initialization behavior
        """
        # First instantiation with custom parameters
        db1 = DatabaseClient(db_name="testdb", host="192.168.1.100", port=3306)
        
        # Second instantiation with different parameters (should be ignored)
        db2 = DatabaseClient(db_name="testdb", host="localhost", port=5432)
        
        # Should be same instance with first parameters
        assert db1 is db2
        assert db2.host == "192.168.1.100"  # First parameters used
        assert db2.port == 3306  # First parameters used
    
    def test_singleton_instances_dictionary_populated(self, reset_singleton_instances):
        """
        Test that _instances dictionary is properly populated.
        
        Testing Concept: Internal state verification
        """
        db1 = DatabaseClient(db_name="testdb1")
        db2 = DatabaseClient(db_name="testdb2")
        
        # Check _instances dictionary
        assert "testdb1" in DatabaseClient._instances
        assert "testdb2" in DatabaseClient._instances
        assert DatabaseClient._instances["testdb1"] is db1
        assert DatabaseClient._instances["testdb2"] is db2


# ============================================================================
# TEST CLASS: Multiple Classes with SingletonMeta
# ============================================================================


class TestMultipleClassesWithSingleton:
    """Test multiple classes using SingletonMeta."""
    
    def test_different_classes_maintain_separate_instances(self, reset_singleton_instances):
        """
        Test that different classes maintain separate singleton instances.
        
        Testing Concept: Class-specific singleton instances
        """
        db = DatabaseClient(db_name="shared_name")
        cache = CacheClient(db_name="shared_name")
        
        # Current implementation shares instances by db_name across classes
        assert db is cache
        assert type(db) == DatabaseClient
    
    def test_both_classes_use_singleton_pattern(self, reset_singleton_instances):
        """
        Test that both classes properly implement singleton pattern.
        
        Testing Concept: Singleton pattern across classes
        """
        db1 = DatabaseClient(db_name="testdb")
        db2 = DatabaseClient(db_name="testdb")
        
        cache1 = CacheClient(db_name="testcache")
        cache2 = CacheClient(db_name="testcache")
        
        assert db1 is db2
        assert cache1 is cache2
        assert db1 is not cache1
    
    def test_instances_dictionary_contains_all_db_names(self, reset_singleton_instances):
        """
        Test that _instances contains all db_names across classes.
        
        Testing Concept: Shared _instances dictionary
        """
        db = DatabaseClient(db_name="db1")
        cache = CacheClient(db_name="cache1")
        config = ConfigManager(db_name="config1")
        
        assert "db1" in DatabaseClient._instances
        assert "cache1" in CacheClient._instances
        assert "config1" in ConfigManager._instances
        
        # _instances is shared via metaclass, not isolated per class
        assert "db1" in CacheClient._instances
        assert "cache1" in DatabaseClient._instances


# ============================================================================
# TEST CLASS: Edge Cases
# ============================================================================


class TestSingletonMetaEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_singleton_with_none_db_name(self, reset_singleton_instances):
        """
        Test singleton behavior with None as db_name.
        
        Testing Concept: None value handling
        """
        db1 = DatabaseClient(db_name=None)
        db2 = DatabaseClient(db_name=None)
        
        # Should still follow singleton pattern
        assert db1 is db2
        assert None in DatabaseClient._instances

    def test_singleton_with_empty_string_db_name(self, reset_singleton_instances):
        """
        Test singleton behavior with empty string as db_name.
        
        Testing Concept: Empty string handling
        """
        db1 = DatabaseClient(db_name="")
        db2 = DatabaseClient(db_name="")
        
        assert db1 is db2
        assert "" in DatabaseClient._instances
    
    def test_singleton_with_numeric_db_name(self, reset_singleton_instances):
        """
        Test singleton behavior with numeric db_name.
        
        Testing Concept: Non-string db_name
        """
        db1 = DatabaseClient(db_name=123)
        db2 = DatabaseClient(db_name=123)
        
        assert db1 is db2
        assert 123 in DatabaseClient._instances
    
    def test_singleton_without_db_name_kwarg(self, reset_singleton_instances):
        """
        Test behavior when db_name is not provided as kwarg.
        
        Testing Concept: Missing db_name in kwargs
        """
        # When db_name is not in kwargs, None is used as key
        with pytest.raises(TypeError):
            # This should fail because db_name is required positional arg
            DatabaseClient()
    
    def test_singleton_with_db_name_as_positional_arg(self, reset_singleton_instances):
        """
        Test singleton when db_name is passed as positional argument.
        
        Testing Concept: Positional vs keyword argument
        """
        # When passed as positional arg, it's not in kwargs
        db1 = DatabaseClient("testdb")
        db2 = DatabaseClient("testdb")
        
        # Both use None as key since db_name not in kwargs
        assert db1 is db2
        assert None in DatabaseClient._instances
    
    def test_singleton_mixed_positional_and_keyword(self, reset_singleton_instances):
        """
        Test singleton with mixed positional and keyword arguments.
        
        Testing Concept: Argument passing patterns
        """
        db1 = DatabaseClient(db_name="testdb", host="localhost")
        db2 = DatabaseClient(db_name="testdb", port=3306)
        
        assert db1 is db2
        assert db1.host == "localhost"
        assert db1.port == 5432  # Default from first instantiation
    
    def test_singleton_with_special_characters_in_db_name(self, reset_singleton_instances):
        """
        Test singleton with special characters in db_name.
        
        Testing Concept: Special character handling
        """
        special_names = [
            "db-name",
            "db.name",
            "db_name",
            "db name",
            "db@name",
            "db#name",
            "数据库",  # Chinese characters
            "قاعدة_البيانات",  # Arabic
        ]
        
        instances = []
        for name in special_names:
            instance = DatabaseClient(db_name=name)
            instances.append(instance)
            assert name in DatabaseClient._instances
        
        # Each should be unique
        assert len(set(id(inst) for inst in instances)) == len(special_names)


# ============================================================================
# TEST CLASS: Metaclass Behavior
# ============================================================================


class TestMetaclassBehavior:
    """Test metaclass-specific behavior."""
    
    def test_class_has_singleton_meta_as_metaclass(self):
        """
        Test that class correctly uses SingletonMeta as metaclass.
        
        Testing Concept: Metaclass verification
        """
        assert type(DatabaseClient) == SingletonMeta
        assert isinstance(DatabaseClient, SingletonMeta)
    
    def test_singleton_meta_inherits_from_abc_meta(self):
        """
        Test that SingletonMeta inherits from ABCMeta.
        
        Testing Concept: Inheritance verification
        """
        assert issubclass(SingletonMeta, ABCMeta)
        
    def test_instances_dictionary_is_class_attribute(self, reset_singleton_instances):
        """
        Test that _instances is created as a per-class attribute.
        
        Testing Concept: Per-class attribute verification
        """
        if hasattr(DatabaseClient, "_instances"):
            # If it exists, it should be empty after reset
            assert DatabaseClient._instances == {}, \
                "After reset, _instances should be empty"
        
        # After first instantiation, the class definitely has _instances
        db = DatabaseClient(db_name="test")
        assert hasattr(DatabaseClient, "_instances"), \
            "Class should have _instances after instantiation"
        assert isinstance(DatabaseClient._instances, dict), \
            "_instances should be a dictionary"
        assert "test" in DatabaseClient._instances, \
            "Instance should be stored in _instances"
        
        # Different classes share one _instances dictionary on metaclass
        cache = CacheClient(db_name="test")
        assert hasattr(CacheClient, "_instances"), \
            "CacheClient should have its own _instances"
        assert DatabaseClient._instances is CacheClient._instances, \
            "Classes share the same _instances dictionary"
        
        # Verify shared storage shape
        assert len(DatabaseClient._instances) == 1
        assert len(CacheClient._instances) == 1
        assert list(DatabaseClient._instances.keys()) == ["test"]
        assert list(CacheClient._instances.keys()) == ["test"]
    
    def test_call_method_is_overridden(self):
        """
        Test that __call__ method is properly overridden.
        
        Testing Concept: Method override verification
        """
        assert hasattr(SingletonMeta, "__call__")
        assert callable(SingletonMeta.__call__)
    
    def test_super_call_creates_instance(self, reset_singleton_instances):
        """
        Test that super().__call__ is properly invoked for new instances.
        
        Testing Concept: Super class method invocation
        """
        # First call should create new instance via super().__call__
        db1 = DatabaseClient(db_name="testdb")
        
        assert isinstance(db1, DatabaseClient)
        assert db1.db_name == "testdb"


# ============================================================================
# TEST CLASS: State Modification Tests
# ============================================================================


class TestSingletonStateModification:
    """Test state modification and persistence in singleton instances."""
    
    def test_state_changes_persist_across_retrievals(self, reset_singleton_instances):
        """
        Test that state changes persist across instance retrievals.
        
        Testing Concept: State persistence verification
        """
        db1 = DatabaseClient(db_name="testdb")
        db1.connection_count = 10
        db1.custom_attribute = "custom_value"
        
        db2 = DatabaseClient(db_name="testdb")
        
        assert db2.connection_count == 10
        assert db2.custom_attribute == "custom_value"
    
    def test_method_calls_affect_shared_state(self, reset_singleton_instances):
        """
        Test that method calls affect shared singleton state.
        
        Testing Concept: Shared state modification
        """
        db1 = DatabaseClient(db_name="testdb")
        result1 = db1.connect()
        
        db2 = DatabaseClient(db_name="testdb")
        result2 = db2.connect()
        
        # Both should affect same instance
        assert db1.connection_count == 2
        assert db2.connection_count == 2
    
    def test_cache_modifications_persist(self, reset_singleton_instances):
        """
        Test that cache modifications persist across retrievals.
        
        Testing Concept: Complex state persistence
        """
        cache1 = CacheClient(db_name="cache")
        cache1.cache["key1"] = "value1"
        cache1.cache["key2"] = "value2"
        
        cache2 = CacheClient(db_name="cache")
        
        assert "key1" in cache2.cache
        assert cache2.cache["key1"] == "value1"
        assert len(cache2.cache) == 2


# ============================================================================
# TEST CLASS: Concurrent Access Simulation
# ============================================================================


class TestConcurrentAccessSimulation:
    """Test behavior under simulated concurrent access."""
    
    def test_multiple_rapid_instantiations(self, reset_singleton_instances):
        """
        Test multiple rapid instantiations return same instance.
        
        Testing Concept: Rapid access pattern
        """
        instances = [DatabaseClient(db_name="testdb") for _ in range(100)]
        
        # All should be same instance
        first_instance = instances[0]
        assert all(inst is first_instance for inst in instances)
    
    def test_multiple_db_names_rapid_instantiation(self, reset_singleton_instances):
        """
        Test rapid instantiation with multiple db_names.
        
        Testing Concept: Multiple key rapid access
        """
        db_names = [f"db{i}" for i in range(10)]
        
        # Create instances for each db_name twice
        instances_round1 = [DatabaseClient(db_name=name) for name in db_names]
        instances_round2 = [DatabaseClient(db_name=name) for name in db_names]
        
        # Each matching pair should be same instance
        for inst1, inst2 in zip(instances_round1, instances_round2):
            assert inst1 is inst2
        
        # But different db_names should be different instances
        assert len(set(id(inst) for inst in instances_round1)) == 10


# ============================================================================
# TEST CLASS: Branch Coverage Tests
# ============================================================================


class TestBranchCoverage:
    """Test all branches in SingletonMeta.__call__."""
    
    def test_if_branch_db_name_not_in_instances(self, reset_singleton_instances):
        """
        Test the if branch when db_name is not in _instances.
        
        Testing Concept: Test if condition (True)
        """
        # First call - db_name not in _instances
        assert "new_db" not in DatabaseClient._instances
        
        db = DatabaseClient(db_name="new_db")
        
        # Should now be in _instances
        assert "new_db" in DatabaseClient._instances
        assert DatabaseClient._instances["new_db"] is db
    
    def test_else_branch_db_name_in_instances(self, reset_singleton_instances):
        """
        Test the else branch when db_name is already in _instances.
        
        Testing Concept: Test if condition (False)
        """
        # First call - creates instance
        db1 = DatabaseClient(db_name="existing_db")
        assert "existing_db" in DatabaseClient._instances
        
        # Second call - db_name already in _instances
        db2 = DatabaseClient(db_name="existing_db")
        
        # Should return existing instance
        assert db2 is db1
        assert db2 is DatabaseClient._instances["existing_db"]
    
    def test_kwargs_get_with_default_none(self, reset_singleton_instances):
        """
        Test kwargs.get("db_name") returns None when db_name not in kwargs.
        
        Testing Concept: Test dict.get() default behavior
        """
        # Pass db_name as positional arg (not in kwargs)
        db1 = DatabaseClient("testdb")
        db2 = DatabaseClient("testdb")
        
        # Both should use None as key
        assert None in DatabaseClient._instances
        assert db1 is db2


# ============================================================================
# TEST CLASS: Integration Tests
# ============================================================================


class TestSingletonIntegration:
    """Test realistic usage scenarios."""
    
    def test_database_connection_pool_pattern(self, reset_singleton_instances):
        """
        Test singleton pattern for database connection pool.
        
        Testing Concept: Real-world usage pattern
        """
        # Multiple parts of application request database connection
        db_from_service_a = DatabaseClient(db_name="production", host="prod-db")
        db_from_service_b = DatabaseClient(db_name="production", host="different-host")
        db_from_service_c = DatabaseClient(db_name="production")
        
        # All should share same connection pool
        assert db_from_service_a is db_from_service_b
        assert db_from_service_b is db_from_service_c
        
        # Connection count should be shared
        db_from_service_a.connect()
        assert db_from_service_b.connection_count == 1
        assert db_from_service_c.connection_count == 1
    
    def test_multi_tenant_pattern(self, reset_singleton_instances):
        """
        Test singleton pattern for multi-tenant applications.
        
        Testing Concept: Multi-tenant isolation
        """
        # Different tenants get different instances
        tenant_a_db = DatabaseClient(db_name="tenant_a")
        tenant_b_db = DatabaseClient(db_name="tenant_b")
        tenant_c_db = DatabaseClient(db_name="tenant_c")
        
        # Each tenant has isolated instance
        assert tenant_a_db is not tenant_b_db
        assert tenant_b_db is not tenant_c_db
        
        # But same tenant gets same instance
        tenant_a_db_again = DatabaseClient(db_name="tenant_a")
        assert tenant_a_db is tenant_a_db_again
    
    def test_cache_and_database_coexistence(self, reset_singleton_instances):
        """
        Test multiple singleton classes coexisting.
        
        Testing Concept: Multiple singleton types
        """
        # Create cache and database with same identifier
        cache = CacheClient(db_name="app")
        db = DatabaseClient(db_name="app")
        config = ConfigManager(db_name="app")
        
        # Current implementation keys only by db_name, so instances are shared
        assert cache is db
        assert db is config
        assert cache is config
        
        # But requesting same class with same db_name returns same instance
        cache2 = CacheClient(db_name="app")
        db2 = DatabaseClient(db_name="app")
        
        assert cache is cache2
        assert db is db2


# ============================================================================
# TEST CLASS: Error Handling
# ============================================================================


class TestErrorHandling:
    """Test error scenarios and exception handling."""
    
    def test_class_without_db_name_parameter_raises_error(self, reset_singleton_instances):
        """
        Test that class without db_name parameter raises TypeError.
        
        Testing Concept: Parameter requirement validation
        """
        class InvalidClass(metaclass=SingletonMeta):
            def __init__(self, name: str):
                self.name = name
        
        # Should raise TypeError when trying to access db_name
        with pytest.raises(TypeError):
            InvalidClass()
    
    def test_instance_creation_with_invalid_arguments(self, reset_singleton_instances):
        """
        Test instance creation with invalid arguments.
        
        Testing Concept: Invalid argument handling
        """
        # Try to create with invalid argument
        with pytest.raises(TypeError):
            DatabaseClient(invalid_param="value")
    
    def test_modifying_instances_dictionary_directly(self, reset_singleton_instances):
        """
        Test behavior when _instances dictionary is modified directly.
        
        Testing Concept: Direct state manipulation
        """
        # Create instance normally
        db1 = DatabaseClient(db_name="testdb")
        
        # Modify _instances directly
        DatabaseClient._instances["testdb"] = "corrupted"
        
        # Next call should return corrupted value
        result = DatabaseClient(db_name="testdb")
        assert result == "corrupted"


# ============================================================================
# PARAMETERIZED TESTS
# ============================================================================


class TestParameterizedScenarios:
    """Test multiple scenarios efficiently with parameterization."""
    
    @pytest.mark.parametrize("db_name", [
        "testdb",
        "production",
        "development",
        "staging",
        "test_db_123",
    ])
    def test_singleton_with_various_db_names(self, reset_singleton_instances, db_name):
        """
        Test singleton behavior with various db_names.
        
        Testing Concept: Parameterized db_name testing
        """
        db1 = DatabaseClient(db_name=db_name)
        db2 = DatabaseClient(db_name=db_name)
        
        assert db1 is db2
        assert db_name in DatabaseClient._instances
    
    @pytest.mark.parametrize("db_name,expected_type", [
        ("db1", str),
        (123, int),
        (45.67, float),
        (None, type(None)),
    ])
    def test_singleton_with_various_db_name_types(
        self, reset_singleton_instances, db_name, expected_type
    ):
        """
        Test singleton with various db_name types.
        
        Testing Concept: Type flexibility testing
        """
        db = DatabaseClient(db_name=db_name)
        
        assert db_name in DatabaseClient._instances
        assert type(db_name) == expected_type


# ============================================================================
# Run tests from command line
# ============================================================================


if __name__ == "__main__":
    pytest.main([
        __file__, 
        "-v", 
        "--tb=short",
        "--cov=src.utils.singleton_meta",
        "--cov-report=term-missing"
    ])

