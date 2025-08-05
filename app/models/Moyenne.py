from sqlalchemy import Column, Integer, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

class Moyenne(Base):
    __tablename__ = "moyenne"

    id = Column(Integer, primary_key=True)
    specialty = Column(JSON, nullable=True)  # List of specialties, e.g., ["Math", "Physics"]
    notes = Column(JSON, nullable=True)  # List of notes, e.g., [{"subject": "Math", "score": 15.5}, ...]
    user_id = Column(Integer, ForeignKey("user.id"), unique=True, index=True, nullable=False)

    # Relationship
    user = relationship("User", back_populates="moyenne")