from sqlalchemy import Column, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Moyenne(Base):
    __tablename__ = "moyenne"

    id = Column(Integer, primary_key=True)
    moyenne_generale = Column(Float, nullable=False)
    moyenne_francais = Column(Float, nullable=True)
    moyenne_philo = Column(Float, nullable=True)
    moyenne_math = Column(Float, nullable=True)
    moyenne_svt = Column(Float, nullable=True)
    moyenne_physique = Column(Float, nullable=True)
    moyenne_anglais = Column(Float, nullable=True)
    user_id = Column(Integer, ForeignKey("user.id"), unique=True, index=True)
    user = relationship("User", backref="moyenne")