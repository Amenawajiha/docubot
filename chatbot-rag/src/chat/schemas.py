"""SQLAlchemy ORM models for database tables."""

from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Index, Integer, Text, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ConversationORM(Base):
    """ORM model for conversations table."""

    # Use schema attribute instead of including schema in __tablename__
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    content = Column(Text, nullable=False)
    # Ensure timezone-aware timestamps and let Postgres set UTC by default
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
    )
    meta_data = Column(JSON, nullable=True)

    # Composite index for efficient queries and ensure table created in `visa` schema
    __table_args__ = (
        Index("idx_user_timestamp", "user_id", "timestamp"),
        {"schema": "visa"},
    )

    def __repr__(self):
        return f"<Conversation(user_id={self.user_id}, timestamp={self.timestamp})>"
