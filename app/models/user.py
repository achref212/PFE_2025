from sqlalchemy import (
    Column, Integer, String, Date, Boolean, DateTime, func, ForeignKey, JSON, Float, text
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
    specialites = Column(JSON, nullable=True)
    filiere = Column(String(255), nullable=True)
    telephone = Column(String(20), nullable=True)
    budget = Column(String(255), nullable=True)

    # New fields
    score = Column(Float, nullable=True)
    idee = Column(String(255), nullable=True)

    # Menu 1/2/3 selections
    orientation_choices = Column(
        JSON,
        nullable=True,
        comment="Sélections des menus d'orientation (domaines formations, métiers, types de formation)"
    )

    riasec_differentiation = Column(
        JSON, nullable=True,
        comment="Résultats RIASEC et valeur de différenciation"
    )
    preferences = Column(
        JSON, nullable=True,
        comment="Questions, types de préférences et réponses des utilisateurs"
    )

    # DB-level default is safer/portable
    est_boursier = Column(Boolean, nullable=False, server_default=text("false"))

    adresse = Column(String(255), nullable=True)
    distance = Column(Float, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    etablissement = Column(String(255), nullable=True)
    academie = Column(String(255), nullable=True)

    # If a plan is deleted, keep the user but null this field
    plan_action_id = Column(
        Integer,
        ForeignKey("plan_actions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Optional: user notes (e.g., [{"subject": "Math", "score": 15.5}, ...])
    notes = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # ------------------------
    # Relationships
    # ------------------------
    plan_action = relationship(
        "PlanAction",
        back_populates="users",
        passive_deletes=True,  # cooperate with ondelete
    )

    # Done/not-done progress per step
    step_progress = relationship(
        "UserStepProgress",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # ------------------------
    # Methods
    # ------------------------
    def set_password(self, password: str) -> None:
        if len(password) < 8:
            raise ValueError("Le mot de passe doit contenir au moins 8 caractères.")
        self.password_hash = pwd_context.hash(password)

    def check_password(self, password: str) -> bool:
        return pwd_context.verify(password, self.password_hash)