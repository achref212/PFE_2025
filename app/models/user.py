from datetime import date
from sqlalchemy import Column, Integer, String, Date, Boolean, Float, DateTime, ARRAY, func
from app.core.database import Base
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(Base):
    __tablename__ = "user"
    __table_args__ = {"comment": "Comptes et profil des étudiants"}

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    nom = Column(String(100), nullable=False)
    prenom = Column(String(100), nullable=False)
    sexe = Column(String(10), nullable=False)
    date_naissance = Column(Date, nullable=False)
    profile_picture = Column(String(255), nullable=True)

    niveau_scolaire = Column(String(50))
    bac_type = Column(String(50))
    specialites = Column(ARRAY(String))

    moyenne_generale = Column(Float)
    moyenne_francais = Column(Float)
    moyenne_philo = Column(Float)
    moyenne_math = Column(Float)
    moyenne_svt = Column(Float)
    moyenne_physique = Column(Float)
    moyenne_anglais = Column(Float)

    telephone = Column(String(20), nullable=True)
    adresse = Column(String(255), nullable=True)
    academie = Column(String(100))
    est_boursier = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def set_password(self, password: str) -> None:
        if len(password) < 6:
            raise ValueError("Le mot de passe doit contenir au moins 6 caractères.")
        self.password_hash = pwd_context.hash(password)

    def check_password(self, password: str) -> bool:
        return pwd_context.verify(password, self.password_hash)