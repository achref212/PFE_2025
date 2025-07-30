from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Location(Base):
    __tablename__ = "location"

    id = Column(Integer, primary_key=True)
    adresse = Column(String(255), nullable=False)
    distance = Column(Float, nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    etablissement = Column(String(255), nullable=False)
    academie = Column(String(255), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), unique=True, index=True)
    user = relationship("User", backref="location")
