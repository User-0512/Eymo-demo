from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from services.database import Base
from pgvector.sqlalchemy import Vector

class Content(Base):
    __tablename__ = "content"
    id = Column(Integer, primary_key=True, index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    subject_tag = Column(String(50), nullable=False)
    difficulty = Column(String(20), default="intermediate") # beginner, intermediate, advanced
    moderation_status = Column(String(20), default="pending_review") # approved, pending_review, rejected
    
    # Using pgvector's Vector type. all-MiniLM-L6-v2 produces 384-dimensional embeddings
    embedding = Column(Vector(384), nullable=True) 
    popularity_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    author = relationship("User", back_populates="contents")

class UserInteraction(Base):
    __tablename__ = "user_interactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    content_id = Column(Integer, nullable=False)
    interaction_type = Column(String(50), nullable=False) # view, like, search
    subject_tag = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
