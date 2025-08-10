from pydantic import BaseModel, EmailStr, Field
from datetime import date, datetime
from typing import Optional, List, Dict

# =========================
# Auth / User create & login
# =========================

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    nom: str
    prenom: str
    sexe: str
    date_naissance: date


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# =========================
# Plan models (PlanAction, PlanStep, UserStepProgress)
# =========================

class PlanStepCreate(BaseModel):
    plan_action_id: int
    titre: str
    description: Optional[str] = None
    ordre: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class PlanStepResponse(BaseModel):
    id: int
    plan_action_id: int
    titre: str
    description: Optional[str] = None
    ordre: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    class Config:
        orm_mode = True


class PlanActionCreate(BaseModel):
    nom: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = True


class PlanActionResponse(BaseModel):
    id: int
    nom: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: bool
    steps: Optional[List[PlanStepResponse]] = None

    class Config:
        orm_mode = True


class UserStepProgressCreate(BaseModel):
    step_id: int
    is_done: bool = True  # default when marking as done


class UserStepProgressUpdate(BaseModel):
    is_done: bool


class UserStepProgressResponse(BaseModel):
    id: int
    user_id: int
    step_id: int
    is_done: bool
    done_at: Optional[datetime] = None

    class Config:
        orm_mode = True


# =========================
# User responses / updates
# =========================

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
    specialites: Optional[List[str]] = None
    filiere: Optional[str] = None
    telephone: Optional[str] = None
    budget: Optional[str] = None

    score: Optional[float] = None
    idee: Optional[str] = None
    orientation_choices: Optional[Dict[str, List[str]]] = None  # Menu 1/2/3
    riasec_differentiation: Optional[Dict] = None
    preferences: Optional[Dict] = None
    notes: Optional[List[Dict]] = None

    est_boursier: Optional[bool] = None
    adresse: Optional[str] = None
    distance: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    etablissement: Optional[str] = None
    academie: Optional[str] = None

    plan_action_id: Optional[int] = None

    # New: expose per-step progress entries
    step_progress: Optional[List[UserStepProgressResponse]] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


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
    filiere: Optional[str] = None
    telephone: Optional[str] = None
    budget: Optional[str] = None

    score: Optional[float] = None
    idee: Optional[str] = None
    orientation_choices: Optional[Dict[str, List[str]]] = None
    riasec_differentiation: Optional[Dict] = None
    preferences: Optional[Dict] = None
    notes: Optional[List[Dict]] = None

    est_boursier: Optional[bool] = None
    adresse: Optional[str] = None
    distance: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    etablissement: Optional[str] = None
    academie: Optional[str] = None

    plan_action_id: Optional[int] = None


# =========================
# Auth token & verification flows
# =========================

class TokenResponse(BaseModel):
    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyCodeRequest(BaseModel):
    email: EmailStr
    code: str


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str
    new_password: str = Field(..., min_length=8)


class VerifyRegistrationRequest(BaseModel):
    email: EmailStr
    code: str