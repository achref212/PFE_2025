from pydantic import BaseModel, EmailStr, Field
from datetime import date, datetime
from typing import Optional, List

# 🔐 Utilisé pour l'inscription
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    nom: str
    prenom: str
    sexe: str
    date_naissance: date

# 🔑 Utilisé pour la connexion
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# 📍 Location models
class LocationCreate(BaseModel):
    adresse: str
    distance: Optional[float] = None
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    etablissement: str
    academie: str

class LocationResponse(BaseModel):
    id: int
    adresse: str
    distance: Optional[float] = None
    latitude: float
    longitude: float
    etablissement: str
    academie: str

    class Config:
        orm_mode = True

# 📊 Moyenne models
class MoyenneCreate(BaseModel):
    generale: float
    francais: Optional[float] = None
    philo: Optional[float] = None
    math: Optional[float] = None
    svt: Optional[float] = None
    physique: Optional[float] = None
    anglais: Optional[float] = None

class MoyenneResponse(BaseModel):
    id: int
    moyenne_generale: float
    moyenne_francais: Optional[float] = None
    moyenne_philo: Optional[float] = None
    moyenne_math: Optional[float] = None
    moyenne_svt: Optional[float] = None
    moyenne_physique: Optional[float] = None
    moyenne_anglais: Optional[float] = None

    class Config:
        orm_mode = True

# 📋 PlanAction models
class PlanActionCreate(BaseModel):
    nom: str

class PlanActionResponse(BaseModel):
    id: int
    nom: str
    steps: Optional[List["PlanStepResponse"]] = None

    class Config:
        orm_mode = True

class PlanStepCreate(BaseModel):
    titre: str

class PlanStepResponse(BaseModel):
    id: int
    titre: str
    plan_action_id: int
    questions: Optional[List["PlanQuestionResponse"]] = None

    class Config:
        orm_mode = True

class PlanQuestionCreate(BaseModel):
    contenu: str

class PlanQuestionResponse(BaseModel):
    id: int
    contenu: str
    step_id: int
    responses: Optional[List["UserPlanResponseResponse"]] = None

    class Config:
        orm_mode = True

class UserPlanResponseCreate(BaseModel):
    question_id: int
    reponse: Optional[str] = None

class UserPlanResponseResponse(BaseModel):
    id: int
    user_id: int
    question_id: int
    reponse: Optional[str] = None

    class Config:
        orm_mode = True

class UserStepAnswerCreate(BaseModel):
    step_id: int
    response: Optional[str] = None

class UserStepAnswerResponse(BaseModel):
    id: int
    user_id: int
    step_id: int
    response: Optional[str] = None

    class Config:
        orm_mode = True

# ✏️ UserPlanUpdateRequest for updating plan responses
class UserPlanUpdateRequest(BaseModel):
    reponses: List[UserPlanResponseCreate]

# ✅ Utilisé dans les réponses (lecture seule)
class UserResponse(BaseModel):
    id: int
    email: EmailStr
    nom: str
    prenom: str
    sexe: str
    date_naissance: date
    profile_picture: Optional[str] = None
    niveau_scolaire: Optional[str] = None
    objectif: Optional[str] = None
    voie: Optional[str] = None
    specialites: Optional[str] = None
    filiere: Optional[str] = None
    telephone: Optional[str] = None
    budget: Optional[str] = None
    est_boursier: Optional[bool] = None
    plan_action: Optional[PlanActionResponse] = None
    location: Optional[LocationResponse] = None
    moyenne: Optional[MoyenneResponse] = None
    step_answers: Optional[List[UserStepAnswerResponse]] = None
    plan_responses: Optional[List[UserPlanResponseResponse]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

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
    specialites: Optional[str] = None
    filiere: Optional[str] = None
    telephone: Optional[str] = None
    budget: Optional[str] = None
    est_boursier: Optional[bool] = None
    plan_action_id: Optional[int] = None

# 🔄 Réinitialisation du mot de passe
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class VerifyCodeRequest(BaseModel):
    email: EmailStr
    code: str

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str
    new_password: str = Field(..., min_length=8)

# ✅ Vérification du code d'inscription
class VerifyRegistrationRequest(BaseModel):
    email: EmailStr
    code: str

# Resolve forward references
PlanActionResponse.update_forward_refs()
PlanStepResponse.update_forward_refs()
PlanQuestionResponse.update_forward_refs()
UserPlanResponseResponse.update_forward_refs()
UserStepAnswerResponse.update_forward_refs()
UserResponse.update_forward_refs()
TokenResponse.update_forward_refs()