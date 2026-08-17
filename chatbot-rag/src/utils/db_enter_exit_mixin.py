"""
Enter Exit Mixin Module
=======================
This module provides a mixin class for managing database sessions.
This is designed to be used with database sessions to ensure proper cleanup.
"""

from src.utils.db_generic import Database
from src.utils.log_helper import logger


class DBEnterExitMixin:
    """
    A mixin class that provides methods for creating and closing a database session.
    It handles exceptions and rollbacks as needed.
    Attributes
    ----------
    _db_session : object
        The current database session.
    Methods
    -------
    __enter__()
        Enters a database session.
    __exit__(exc_type, exc_val, exc_tb)
        Exits a database session, handling exceptions and rollbacks as needed.
    """

    def __enter__(self):
        self._db_helper = self._db_helper or Database(
            db_schema="schengendb", db_name="postgresql"
        )

        self._db_session = self._db_helper.session()

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.info("Closing DB session..")
        self._db_session.close()
        if exc_type is not None:
            self._db_session.rollback()
