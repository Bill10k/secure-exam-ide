from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func

from .database import Base

class ExamSession(Base):
    __tablename__ = "exam_sessions"

    id = Column(Integer, primary_key=True, index=True)
    # LTI Context
    context_id = Column(String, index=True)
    resource_link_id = Column(String, index=True)
    user_id = Column(String, index=True)
    
    # Store the raw JWT or specific claims needed for AGS sync later
    raw_jwt = Column(Text, nullable=True)
    
    # Session tracking
    status = Column(String, default="initialized") # initialized, started, submitted
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
