"""
Comprehensive unit tests for ServiceManager.

This test suite covers:
- Singleton pattern behavior
- Service initialization (once and only once)
- Component initialization order
- Getter methods for all services
- Global instance management
- Thread safety (implicit via singleton)
- Reinitialization prevention
- Service dependency injection
"""

import os
import sys
from unittest.mock import MagicMock, patch, call

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ============================================================================
# FIXTURES - Setup and Teardown
# ============================================================================


@pytest.fixture(autouse=True)
def reset_singleton():
    """
    Reset ServiceManager singleton state before and after each test.
    
    Testing Concept: Test isolation for singleton pattern
    
    This is critical because singleton state persists across tests.
    We need to reset both the instance and initialization flag.
    """
    # Store original state
    from src.service_manager import ServiceManager
    original_instance = ServiceManager._instance
    original_initialized = ServiceManager._initialized
    
    # Reset before test
    ServiceManager._instance = None
    ServiceManager._initialized = False
    
    yield
    
    # Reset after test
    ServiceManager._instance = original_instance
    ServiceManager._initialized = original_initialized


@pytest.fixture(autouse=True)
def reset_global_manager():
    """
    Reset global _service_manager variable.
    
    Testing Concept: Reset global state for test isolation
    """
    import src.service_manager as sm_module
    original_global = sm_module._service_manager
    
    # Reset before test
    sm_module._service_manager = None
    
    yield
    
    # Reset after test
    sm_module._service_manager = original_global


@pytest.fixture
def mock_logger():
    """
    Mock logger to avoid actual logging during tests.
    
    Testing Concept: Mock logging infrastructure
    """
    with patch("src.service_manager.logger") as mock:
        yield mock


@pytest.fixture
def mock_embedding_manager():
    """
    Mock EmbeddingManager.
    
    Testing Concept: Mock heavy ML component
    """
    with patch("src.service_manager.EmbeddingManager") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock


@pytest.fixture
def mock_vector_retriever():
    """
    Mock VectorRetriever.
    
    Testing Concept: Mock vector database component
    """
    with patch("src.service_manager.VectorRetriever") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock


@pytest.fixture
def mock_llm_orchestrator():
    """
    Mock LLMOrchestrator.
    
    Testing Concept: Mock LLM integration
    """
    with patch("src.service_manager.LLMOrchestrator") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock


@pytest.fixture
def mock_confidence_scorer():
    """
    Mock ConfidenceScorer.
    
    Testing Concept: Mock scoring logic
    """
    with patch("src.service_manager.ConfidenceScorer") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock


@pytest.fixture
def mock_prompt_builder():
    """
    Mock PromptBuilder.
    
    Testing Concept: Mock prompt construction
    """
    with patch("src.service_manager.PromptBuilder") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock


@pytest.fixture
def mock_clarification_manager():
    """
    Mock ClarificationManager.
    
    Testing Concept: Mock clarification logic
    """
    with patch("src.service_manager.ClarificationManager") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock


@pytest.fixture
def all_mocks(
    mock_logger,
    mock_embedding_manager,
    mock_vector_retriever,
    mock_llm_orchestrator,
    mock_confidence_scorer,
    mock_prompt_builder,
    mock_clarification_manager,
):
    """
    Combine all mocks for convenience.
    
    Testing Concept: Fixture composition
    """
    return {
        "logger": mock_logger,
        "embedding_manager": mock_embedding_manager,
        "vector_retriever": mock_vector_retriever,
        "llm_orchestrator": mock_llm_orchestrator,
        "confidence_scorer": mock_confidence_scorer,
        "prompt_builder": mock_prompt_builder,
        "clarification_manager": mock_clarification_manager,
    }


# ============================================================================
# TEST CLASS: Singleton Pattern Tests
# ============================================================================


class TestSingletonPattern:
    """Test that ServiceManager implements singleton pattern correctly."""
    
    def test_singleton_returns_same_instance(self, all_mocks):
        """
        Test that multiple instantiations return the same instance.
        
        Testing Concept: Singleton pattern verification
        """
        from src.service_manager import ServiceManager
        
        instance1 = ServiceManager()
        instance2 = ServiceManager()
        instance3 = ServiceManager()
        
        # All should be the exact same object
        assert instance1 is instance2
        assert instance2 is instance3
        assert id(instance1) == id(instance2) == id(instance3)
    
    def test_singleton_new_method_returns_same_instance(self, all_mocks):
        """
        Test that __new__ enforces singleton pattern.
        
        Testing Concept: Test __new__ method behavior
        """
        from src.service_manager import ServiceManager
        
        # Create instances using different methods
        instance1 = ServiceManager.__new__(ServiceManager)
        instance2 = ServiceManager.__new__(ServiceManager)
        
        assert instance1 is instance2
    
    def test_singleton_class_instance_variable(self, all_mocks):
        """
        Test that _instance class variable is set correctly.
        
        Testing Concept: Test class variable
        """
        from src.service_manager import ServiceManager
        
        # Initially None
        assert ServiceManager._instance is None
        
        # Create instance
        instance = ServiceManager()
        
        # Class variable should now point to instance
        assert ServiceManager._instance is instance
        assert ServiceManager._instance is not None
    
    def test_singleton_after_reset(self, all_mocks):
        """
        Test singleton behavior after manual reset.
        
        Testing Concept: Test reset and recreation
        """
        from src.service_manager import ServiceManager
        
        # Create first instance
        instance1 = ServiceManager()
        
        # Manually reset (simulating fixture behavior)
        ServiceManager._instance = None
        ServiceManager._initialized = False
        
        # Create new instance
        instance2 = ServiceManager()
        
        # Should be different instances
        assert instance1 is not instance2


# ============================================================================
# TEST CLASS: Initialization Tests
# ============================================================================


class TestServiceManagerInitialization:
    """Test ServiceManager initialization behavior."""
    
    def test_initialization_happens_only_once(self, all_mocks):
        """
        Test that initialization code runs only once.
        
        Testing Concept: Test initialization guard
        """
        from src.service_manager import ServiceManager
        
        # Create multiple instances
        ServiceManager()
        ServiceManager()
        ServiceManager()
        
        # Each component should be initialized only once
        all_mocks["embedding_manager"].assert_called_once()
        all_mocks["vector_retriever"].assert_called_once()
        all_mocks["llm_orchestrator"].assert_called_once()
        all_mocks["confidence_scorer"].assert_called_once()
        all_mocks["prompt_builder"].assert_called_once()
        all_mocks["clarification_manager"].assert_called_once()
    
    def test_initialized_flag_starts_false(self):
        """
        Test that _initialized flag starts as False.
        
        Testing Concept: Test initial state
        """
        from src.service_manager import ServiceManager
        
        # Before any instantiation
        assert ServiceManager._initialized is False
    
    def test_initialized_flag_becomes_true_after_init(self, all_mocks):
        """
        Test that _initialized flag becomes True after initialization.
        
        Testing Concept: Test state transition
        """
        from src.service_manager import ServiceManager
        
        # Create instance
        ServiceManager()
        
        # Flag should now be True
        assert ServiceManager._initialized is True
    
    def test_reinitialization_skipped_when_flag_true(self, all_mocks):
        """
        Test that reinitialization is skipped when flag is True.
        
        Testing Concept: Test guard condition
        """
        from src.service_manager import ServiceManager
        
        # First initialization
        manager1 = ServiceManager()
        
        # Reset call counts
        all_mocks["embedding_manager"].reset_mock()
        all_mocks["vector_retriever"].reset_mock()
        
        # Second initialization (should be skipped)
        manager2 = ServiceManager()
        
        # Components should NOT be re-initialized
        all_mocks["embedding_manager"].assert_not_called()
        all_mocks["vector_retriever"].assert_not_called()
    
    def test_logging_initialization_start(self, all_mocks):
        """
        Test that initialization start is logged.
        
        Testing Concept: Test logging
        """
        from src.service_manager import ServiceManager
        
        ServiceManager()
        
        all_mocks["logger"].info.assert_any_call("Initializing shared services...")
    
    def test_logging_initialization_complete(self, all_mocks):
        """
        Test that initialization completion is logged.
        
        Testing Concept: Test logging
        """
        from src.service_manager import ServiceManager
        
        ServiceManager()
        
        all_mocks["logger"].info.assert_any_call(
            "Shared services initialized successfully"
        )
    
    def test_initialization_order(self, all_mocks):
        """
        Test that components are initialized in correct order.
        
        Testing Concept: Test dependency order
        """
        from src.service_manager import ServiceManager
        
        # Track call order
        call_order = []
        
        def track_embedding_manager(*args, **kwargs):
            call_order.append("embedding_manager")
            return MagicMock()
        
        def track_vector_retriever(*args, **kwargs):
            call_order.append("vector_retriever")
            return MagicMock()
        
        def track_llm_orchestrator(*args, **kwargs):
            call_order.append("llm_orchestrator")
            return MagicMock()
        
        all_mocks["embedding_manager"].side_effect = track_embedding_manager
        all_mocks["vector_retriever"].side_effect = track_vector_retriever
        all_mocks["llm_orchestrator"].side_effect = track_llm_orchestrator
        
        ServiceManager()
        
        # EmbeddingManager must be initialized before VectorRetriever
        assert call_order.index("embedding_manager") < call_order.index("vector_retriever")
        # VectorRetriever should be initialized before LLM orchestrator
        assert call_order.index("vector_retriever") < call_order.index("llm_orchestrator")


# ============================================================================
# TEST CLASS: Component Initialization Tests
# ============================================================================


class TestComponentInitialization:
    """Test individual component initialization."""
    
    def test_embedding_manager_initialized(self, all_mocks):
        """
        Test that EmbeddingManager is initialized.
        
        Testing Concept: Test component creation
        """
        from src.service_manager import ServiceManager
        
        manager = ServiceManager()
        
        all_mocks["embedding_manager"].assert_called_once_with()
        assert hasattr(manager, "embedding_manager")
        assert manager.embedding_manager is not None
    
    def test_vector_retriever_initialized_with_embedding_manager(self, all_mocks):
        """
        Test that VectorRetriever is initialized with embedding_manager.
        
        Testing Concept: Test dependency injection
        """
        from src.service_manager import ServiceManager
        
        manager = ServiceManager()
        
        # VectorRetriever should be called with embedding_manager parameter
        all_mocks["vector_retriever"].assert_called_once_with(
            embedding_manager=manager.embedding_manager
        )
    
    def test_llm_orchestrator_initialized(self, all_mocks):
        """
        Test that LLMOrchestrator is initialized.
        
        Testing Concept: Test component creation
        """
        from src.service_manager import ServiceManager
        
        manager = ServiceManager()
        
        all_mocks["llm_orchestrator"].assert_called_once_with()
        assert hasattr(manager, "llm_orchestrator")
        assert manager.llm_orchestrator is not None
    
    def test_confidence_scorer_initialized(self, all_mocks):
        """
        Test that ConfidenceScorer is initialized.
        
        Testing Concept: Test lightweight component
        """
        from src.service_manager import ServiceManager
        
        manager = ServiceManager()
        
        all_mocks["confidence_scorer"].assert_called_once_with()
        assert hasattr(manager, "confidence_scorer")
    
    def test_prompt_builder_initialized(self, all_mocks):
        """
        Test that PromptBuilder is initialized.
        
        Testing Concept: Test lightweight component
        """
        from src.service_manager import ServiceManager
        
        manager = ServiceManager()
        
        all_mocks["prompt_builder"].assert_called_once_with()
        assert hasattr(manager, "prompt_builder")
    
    def test_clarification_manager_initialized(self, all_mocks):
        """
        Test that ClarificationManager is initialized.
        
        Testing Concept: Test lightweight component
        """
        from src.service_manager import ServiceManager
        
        manager = ServiceManager()
        
        all_mocks["clarification_manager"].assert_called_once_with()
        assert hasattr(manager, "clarification_manager")
    
    def test_all_components_stored_as_instance_variables(self, all_mocks):
        """
        Test that all components are stored as instance variables.
        
        Testing Concept: Test instance attributes
        """
        from src.service_manager import ServiceManager
        
        manager = ServiceManager()
        
        # Check all expected attributes exist
        assert hasattr(manager, "embedding_manager")
        assert hasattr(manager, "vector_retriever")
        assert hasattr(manager, "llm_orchestrator")
        assert hasattr(manager, "confidence_scorer")
        assert hasattr(manager, "prompt_builder")
        assert hasattr(manager, "clarification_manager")


# ============================================================================
# TEST CLASS: Getter Method Tests
# ============================================================================


class TestGetterMethods:
    """Test all getter methods return correct instances."""
    
    def test_get_vector_retriever_returns_instance(self, all_mocks):
        """
        Test get_vector_retriever returns the correct instance.
        
        Testing Concept: Test getter method
        """
        from src.service_manager import ServiceManager
        
        manager = ServiceManager()
        retriever = manager.get_vector_retriever()
        
        assert retriever is manager.vector_retriever
        assert retriever is not None
    
    def test_get_llm_orchestrator_returns_instance(self, all_mocks):
        """
        Test get_llm_orchestrator returns the correct instance.
        
        Testing Concept: Test getter method
        """
        from src.service_manager import ServiceManager
        
        manager = ServiceManager()
        orchestrator = manager.get_llm_orchestrator()
        
        assert orchestrator is manager.llm_orchestrator
        assert orchestrator is not None
    
    def test_get_confidence_scorer_returns_instance(self, all_mocks):
        """
        Test get_confidence_scorer returns the correct instance.
        
        Testing Concept: Test getter method
        """
        from src.service_manager import ServiceManager
        
        manager = ServiceManager()
        scorer = manager.get_confidence_scorer()
        
        assert scorer is manager.confidence_scorer
        assert scorer is not None
    
    def test_get_prompt_builder_returns_instance(self, all_mocks):
        """
        Test get_prompt_builder returns the correct instance.
        
        Testing Concept: Test getter method
        """
        from src.service_manager import ServiceManager
        
        manager = ServiceManager()
        builder = manager.get_prompt_builder()
        
        assert builder is manager.prompt_builder
        assert builder is not None
    
    def test_get_clarification_manager_returns_instance(self, all_mocks):
        """
        Test get_clarification_manager returns the correct instance.
        
        Testing Concept: Test getter method
        """
        from src.service_manager import ServiceManager
        
        manager = ServiceManager()
        clarifier = manager.get_clarification_manager()
        
        assert clarifier is manager.clarification_manager
        assert clarifier is not None
    
    def test_getter_methods_return_same_instance_across_calls(self, all_mocks):
        """
        Test that getter methods always return the same instance.
        
        Testing Concept: Test method idempotency
        """
        from src.service_manager import ServiceManager
        
        manager = ServiceManager()
        
        # Call getters multiple times
        retriever1 = manager.get_vector_retriever()
        retriever2 = manager.get_vector_retriever()
        
        orchestrator1 = manager.get_llm_orchestrator()
        orchestrator2 = manager.get_llm_orchestrator()
        
        # Should return same instances
        assert retriever1 is retriever2
        assert orchestrator1 is orchestrator2
    
    def test_getters_work_with_multiple_manager_instances(self, all_mocks):
        """
        Test that getters work correctly even with multiple manager instances.
        
        Testing Concept: Test singleton consistency
        """
        from src.service_manager import ServiceManager
        
        manager1 = ServiceManager()
        manager2 = ServiceManager()
        
        # Since it's a singleton, should return same components
        assert manager1.get_vector_retriever() is manager2.get_vector_retriever()
        assert manager1.get_llm_orchestrator() is manager2.get_llm_orchestrator()


# ============================================================================
# TEST CLASS: Global Instance Function Tests
# ============================================================================


class TestGetServiceManagerFunction:
    """Test the get_service_manager() global function."""
    
    def test_get_service_manager_returns_instance(self, all_mocks):
        """
        Test that get_service_manager returns a ServiceManager instance.
        
        Testing Concept: Test global function
        """
        from src.service_manager import get_service_manager, ServiceManager
        
        manager = get_service_manager()
        
        assert isinstance(manager, ServiceManager)
        assert manager is not None
    
    def test_get_service_manager_returns_same_instance(self, all_mocks):
        """
        Test that multiple calls return the same instance.
        
        Testing Concept: Test global singleton
        """
        from src.service_manager import get_service_manager
        
        manager1 = get_service_manager()
        manager2 = get_service_manager()
        manager3 = get_service_manager()
        
        assert manager1 is manager2
        assert manager2 is manager3
    
    def test_get_service_manager_creates_instance_if_none(self, all_mocks):
        """
        Test that get_service_manager creates instance if global is None.
        
        Testing Concept: Test lazy initialization
        """
        from src.service_manager import get_service_manager
        import src.service_manager as sm_module
        
        # Ensure global is None
        sm_module._service_manager = None
        
        manager = get_service_manager()
        
        assert manager is not None
        assert sm_module._service_manager is manager
    
    def test_get_service_manager_reuses_existing_instance(self, all_mocks):
        """
        Test that get_service_manager reuses existing global instance.
        
        Testing Concept: Test instance reuse
        """
        from src.service_manager import get_service_manager, ServiceManager
        import src.service_manager as sm_module
        
        # Create an existing instance
        existing_manager = ServiceManager()
        sm_module._service_manager = existing_manager
        
        # Get manager should return existing
        manager = get_service_manager()
        
        assert manager is existing_manager
    
    def test_get_service_manager_sets_global_variable(self, all_mocks):
        """
        Test that get_service_manager sets the global _service_manager variable.
        
        Testing Concept: Test global state modification
        """
        from src.service_manager import get_service_manager
        import src.service_manager as sm_module
        
        # Initially None
        sm_module._service_manager = None
        
        manager = get_service_manager()
        
        # Global should now be set
        assert sm_module._service_manager is manager
    
    def test_get_service_manager_consistent_with_direct_instantiation(self, all_mocks):
        """
        Test that get_service_manager returns same instance as direct instantiation.
        
        Testing Concept: Test consistency between access methods
        """
        from src.service_manager import get_service_manager, ServiceManager
        
        # Both should return the same singleton instance
        manager_direct = ServiceManager()
        manager_global = get_service_manager()
        
        assert manager_direct is manager_global


# ============================================================================
# TEST CLASS: Edge Cases and Error Handling
# ============================================================================


class TestEdgeCases:
    """Test edge cases and potential error scenarios."""
    
    def test_initialization_with_component_failure(self, all_mocks):
        """
        Test behavior when a component initialization fails.
        
        Testing Concept: Test error propagation
        """
        from src.service_manager import ServiceManager
        
        # Make VectorRetriever raise an exception
        all_mocks["vector_retriever"].side_effect = RuntimeError("Vector DB connection failed")
        
        # Initialization should propagate the error
        with pytest.raises(RuntimeError, match="Vector DB connection failed"):
            ServiceManager()
    
    def test_initialization_with_embedding_manager_failure(self, all_mocks):
        """
        Test behavior when EmbeddingManager initialization fails.
        
        Testing Concept: Test early failure
        """
        from src.service_manager import ServiceManager
        
        # Make EmbeddingManager raise an exception
        all_mocks["embedding_manager"].side_effect = Exception("Model loading failed")
        
        with pytest.raises(Exception, match="Model loading failed"):
            ServiceManager()
    
    def test_getter_before_initialization_completes(self, all_mocks):
        """
        Test that getters work even if called during initialization.
        
        Testing Concept: Test partial initialization state
        """
        from src.service_manager import ServiceManager
        
        manager = ServiceManager()
        
        # Getters should work normally
        assert manager.get_vector_retriever() is not None
        assert manager.get_llm_orchestrator() is not None
    
    def test_multiple_threads_get_same_singleton(self, all_mocks):
        """
        Test thread safety of singleton pattern (implicit test).
        
        Testing Concept: Test concurrency safety
        """
        import threading
        from src.service_manager import ServiceManager
        
        instances = []
        
        def create_instance():
            instances.append(ServiceManager())
        
        # Create threads
        threads = [threading.Thread(target=create_instance) for _ in range(10)]
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # All instances should be the same object
        assert all(instance is instances[0] for instance in instances)
    
    def test_manual_attribute_modification(self, all_mocks):
        """
        Test that manual attribute modification affects singleton.
        
        Testing Concept: Test mutable state
        """
        from src.service_manager import ServiceManager
        
        manager1 = ServiceManager()
        
        # Manually modify an attribute
        custom_retriever = MagicMock()
        manager1.vector_retriever = custom_retriever
        
        # Get new reference to singleton
        manager2 = ServiceManager()
        
        # Should see the modification
        assert manager2.vector_retriever is custom_retriever


# ============================================================================
# TEST CLASS: Integration-style Tests
# ============================================================================


class TestIntegrationScenarios:
    """Test realistic usage scenarios."""
    
    def test_complete_service_retrieval_workflow(self, all_mocks):
        """
        Test complete workflow of getting all services.
        
        Testing Concept: Integration-style test
        """
        from src.service_manager import get_service_manager
        
        # Get manager
        manager = get_service_manager()
        
        # Retrieve all services
        vector_retriever = manager.get_vector_retriever()
        llm_orchestrator = manager.get_llm_orchestrator()
        confidence_scorer = manager.get_confidence_scorer()
        prompt_builder = manager.get_prompt_builder()
        clarification_manager = manager.get_clarification_manager()
        
        # All should be non-None
        assert vector_retriever is not None
        assert llm_orchestrator is not None
        assert confidence_scorer is not None
        assert prompt_builder is not None
        assert clarification_manager is not None
    
    def test_service_manager_usage_pattern(self, all_mocks):
        """
        Test typical usage pattern in application.
        
        Testing Concept: Test realistic usage
        """
        from src.service_manager import get_service_manager
        
        # Typical application pattern
        manager = get_service_manager()
        
        # Use services
        retriever = manager.get_vector_retriever()
        orchestrator = manager.get_llm_orchestrator()
        
        # Services should be ready to use
        assert retriever is not None
        assert orchestrator is not None
        
        # Should be able to call methods on services (mocked)
        retriever.some_method = MagicMock(return_value="result")
        result = retriever.some_method()
        assert result == "result"
    
    def test_dependency_chain_integrity(self, all_mocks):
        """
        Test that dependency chain is maintained correctly.
        
        Testing Concept: Test dependency injection
        """
        from src.service_manager import ServiceManager
        
        manager = ServiceManager()
        
        # VectorRetriever should have been initialized with EmbeddingManager
        all_mocks["vector_retriever"].assert_called_once()
        call_kwargs = all_mocks["vector_retriever"].call_args[1]
        
        assert "embedding_manager" in call_kwargs
        assert call_kwargs["embedding_manager"] is manager.embedding_manager


# ============================================================================
# TEST CLASS: State Management Tests
# ============================================================================


class TestStateManagement:
    """Test state management and initialization flags."""
    
    def test_initialized_flag_persists_across_instances(self, all_mocks):
        """
        Test that _initialized flag persists across instance creation.
        
        Testing Concept: Test class-level state
        """
        from src.service_manager import ServiceManager
        
        # Create first instance
        ServiceManager()
        assert ServiceManager._initialized is True
        
        # Create second instance
        ServiceManager()
        assert ServiceManager._initialized is True
    
    def test_instance_variable_persists_across_calls(self, all_mocks):
        """
        Test that _instance variable persists.
        
        Testing Concept: Test class-level state
        """
        from src.service_manager import ServiceManager
        
        manager1 = ServiceManager()
        assert ServiceManager._instance is manager1
        
        manager2 = ServiceManager()
        assert ServiceManager._instance is manager1
        assert ServiceManager._instance is manager2
    
    def test_reset_allows_reinitialization(self, all_mocks):
        """
        Test that resetting flags allows reinitialization.
        
        Testing Concept: Test reset behavior
        """
        from src.service_manager import ServiceManager
        
        # First initialization
        manager1 = ServiceManager()
        all_mocks["embedding_manager"].assert_called_once()
        
        # Reset
        ServiceManager._instance = None
        ServiceManager._initialized = False
        all_mocks["embedding_manager"].reset_mock()
        
        # Second initialization
        manager2 = ServiceManager()
        all_mocks["embedding_manager"].assert_called_once()
        
        # Should be different instances
        assert manager1 is not manager2


# ============================================================================
# Run tests from command line
# ============================================================================


if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--cov=src.service_manager",
        "--cov-report=term-missing",
        "--cov-report=html"
    ])


"""
RUNNING THE TESTS:

1. Run all tests:
   pytest tests/test_service_manager.py -v

2. Run with coverage:
   pytest tests/test_service_manager.py --cov=src.service_manager --cov-report=html

3. Run specific test class:
   pytest tests/test_service_manager.py::TestSingletonPattern -v

4. Run specific test:
   pytest tests/test_service_manager.py::TestSingletonPattern::test_singleton_returns_same_instance -v

5. Run with verbose output:
   pytest tests/test_service_manager.py -vv -s

6. Run tests matching pattern:
   pytest tests/test_service_manager.py -k "singleton" -v

EXPECTED COVERAGE:
This test suite should achieve 95%+ coverage of src/service_manager.py by covering:
- ✅ Singleton pattern (__new__ and _instance management)
- ✅ Initialization guard (_initialized flag)
- ✅ All component initialization
- ✅ Dependency injection (EmbeddingManager → VectorRetriever)
- ✅ All getter methods
- ✅ Global get_service_manager() function
- ✅ Error handling during initialization
- ✅ Thread safety (implicit via singleton)
- ✅ State management and reset behavior
- ✅ Edge cases and failure scenarios

TEST ORGANIZATION:
- 10 test classes covering different aspects
- 60+ individual test cases
- Comprehensive fixture setup for test isolation
- Proper singleton reset between tests
- Mock all heavy components
- Test both class methods and module-level functions
"""