from pydantic import BaseModel, EmailStr
from datetime import date
from typing import Optional, List

# 🔐 Utilisé pour l'inscription
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    nom: str
    prenom: str
    sexe: str
    date_naissance: date

# 🔑 Utilisé pour la connexion
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# ✅ Utilisé dans les réponses (lecture seule)
class UserResponse(BaseModel):
    id: int
    email: EmailStr
    nom: str
    prenom: str
    sexe: Optional[str] = None
    date_naissance: Optional[date] = None
    profile_picture: Optional[str] = None

    niveau_scolaire: Optional[str] = None
    objectif: Optional[str] = None
    voie: Optional[str] = None
    specialites: Optional[List[str]] = None
    filiere: Optional[List[str]] = None

    moyenne_generale: Optional[float] = None
    moyenne_francais: Optional[float] = None
    moyenne_philo: Optional[float] = None
    moyenne_math: Optional[float] = None
    moyenne_svt: Optional[float] = None
    moyenne_physique: Optional[float] = None
    moyenne_anglais: Optional[float] = None

    telephone: Optional[str] = None
    adresse: Optional[str] = None
    distance: Optional[str] = None
    budget: Optional[str] = None

    academie: Optional[str] = None
    est_boursier: Optional[bool] = None
    plan_action: Optional[List[str]] = None

    class Config:
        orm_mode = True

# 🔐 Token après authentification
class TokenResponse(BaseModel):
    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str

# ✏️ Mise à jour partielle du profil
class UserUpdate(BaseModel):
    nom: Optional[str] = None
    prenom: Optional[str] = None
    sexe: Optional[str] = None
    date_naissance: Optional[date] = None
    profile_picture: Optional[str] = None

    niveau_scolaire: Optional[str] = None
    objectif: Optional[str] = None
    voie: Optional[str] = None
    specialites: Optional[List[str]] = None
    filiere: Optional[List[str]] = None

    moyenne_generale: Optional[float] = None
    moyenne_francais: Optional[float] = None
    moyenne_philo: Optional[float] = None
    moyenne_math: Optional[float] = None
    moyenne_svt: Optional[float] = None
    moyenne_physique: Optional[float] = None
    moyenne_anglais: Optional[float] = None

    telephone: Optional[str] = None
    adresse: Optional[str] = None
    distance: Optional[str] = None
    budget: Optional[str] = None

    academie: Optional[str] = None
    est_boursier: Optional[bool] = None
    plan_action: Optional[List[str]] = None

# 🔄 Réinitialisation du mot de passe
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class VerifyCodeRequest(BaseModel):
    email: EmailStr
    code: str

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str
    new_password: str

# ✅ Vérification du code d'inscription
class VerifyRegistrationRequest(BaseModel):
    email: EmailStr
    code: str