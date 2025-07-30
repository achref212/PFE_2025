from datetime import date
from sqlalchemy import (
    Column, Integer, String, Date, Boolean, DateTime, func, ForeignKey
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(Base):
    __tablename__ = "user"
    __table_args__ = {"comment": "Comptes et profil des étudiants"}

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(254), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    nom = Column(String(200), nullable=False)
    prenom = Column(String(200), nullable=False)
    sexe = Column(String(20), nullable=False)
    date_naissance = Column(Date, nullable=False)
    profile_picture = Column(String(255), nullable=True)
    objectif = Column(String(255), nullable=True)
    niveau_scolaire = Column(String(250), nullable=True)
    voie = Column(String(250), nullable=True)
    specialites = Column(String(300), nullable=True)  # Si plusieurs, séparées par virgule
    filiere = Column(String(255), nullable=True)
    telephone = Column(String(20), nullable=True)
    budget = Column(String(255), nullable=True)
    est_boursier = Column(Boolean, default=False)
    plan_action_id = Column(Integer, ForeignKey("plan_actions.id"), nullable=True)
    plan_action = relationship("PlanAction", backref="users")
    moyenne_id = Column(Integer, ForeignKey("moyenne.id"), nullable=True, unique=True)
    location_id = Column(Integer, ForeignKey("location.id"), nullable=True, unique=True)
    step_answers = relationship("UserStepAnswer", back_populates="user", cascade="all, delete-orphan")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    # Relations
    plan_action = relationship("PlanAction", backref="users")
    step_answers = relationship("UserStepAnswer", back_populates="user", cascade="all, delete-orphan")
    plan_responses = relationship("UserPlanResponse", back_populates="user", cascade="all, delete-orphan")
    def set_password(self, password: str) -> None:
        if len(password) < 8:
            raise ValueError("Le mot de passe doit contenir au moins 8 caractères.")
        self.password_hash = pwd_context.hash(password)

    def check_password(self, password: str) -> bool:
        return pwd_context.verify(password, self.password_hash)