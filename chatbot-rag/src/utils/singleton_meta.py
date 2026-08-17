"""Abstract base class for singleton pattern."""
from abc import ABCMeta


class SingletonMeta(ABCMeta):
    """
    It's called SingletonMeta because it's a metaclass used to create a Singleton class.
    We're creating a new metaclass SingletonMeta that is inherited from type. 
    This allows us to customize class creation by overriding the __call__ method.
    In this case, we're customizing it to ensure that only one instance if the class exists.
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if kwargs.get("db_name") not in cls._instances:
            cls._instances[kwargs.get("db_name")] = super(SingletonMeta, cls).__call__(
                *args, **kwargs
            )
        return cls._instances[kwargs.get("db_name")]
    