"""SQLAlchemy ORM models for SQLite persistence."""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Float, func
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class ConversationMemory(Base):
    """Stores per-customer chat history for Gemini context."""
    __tablename__ = "conversation_memory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone = Column(String(20), nullable=False, index=True)
    role = Column(String(10), nullable=False)          # "user" or "model"
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<ConversationMemory phone={self.phone} role={self.role}>"


class Customer(Base):
    """Persistent customer profile and preferences."""
    __tablename__ = "customers"

    phone = Column(String(20), primary_key=True)
    name = Column(String(100), nullable=True)
    preferences = Column(Text, nullable=True)          # free-text notes
    favorite_service = Column(String(100), nullable=True)
    preferred_stylist = Column(String(100), nullable=True)
    visit_count = Column(Integer, default=0, nullable=False)
    last_visit = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Customer phone={self.phone} name={self.name}>"
