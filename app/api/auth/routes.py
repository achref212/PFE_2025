from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_jwt_auth import AuthJWT
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.core.database import SessionLocal
from app.models.user import User
from app.api.auth.schemas import (
    UserCreate, UserResponse, LoginRequest, TokenResponse, UserUpdate,
    ForgotPasswordRequest, VerifyCodeRequest, ResetPasswordRequest,
    VerifyRegistrationRequest
)
from app.core.email import send_registration_code_email, send_reset_code_email, EmailNotExistError
from app.core.config import settings
from passlib.context import CryptContext
import random
import string
from typing import Dict
import re
import logging
logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# In-memory storage for pending registrations (email -> {code, user_data, expires_at})
pending_registrations: Dict[str, dict] = {}
CODE_EXPIRATION_MINUTES = 30  # Codes expire after 30 minutes

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def generate_code(length=6):
    return ''.join(random.choices(string.digits, k=length))

def is_code_expired(expires_at: datetime) -> bool:
    return datetime.now() > expires_at

# Email validation regex (basic but strict enough for common use cases)
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

def is_valid_email(email: str) -> bool:
    """Validate email format using regex and basic checks."""
    if not email or not isinstance(email, str):
        return False
    if not EMAIL_REGEX.match(email):
        return False
    return True

@router.post("/register", status_code=status.HTTP_202_ACCEPTED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    # Validate email format before proceeding
    if not is_valid_email(user_in.email):
        raise HTTPException(
            status_code=400,
            detail="Format d'email invalide. Veuillez fournir une adresse email valide (exemple: user@example.com)."
        )

    # Check if email already exists in the database
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=409, detail="Email déjà utilisé")

    # Generate verification code
    code = generate_code()

    # Attempt to send verification email and verify email existence
    try:
        send_registration_code_email(to_email=user_in.email, code=code, verification_token="")
    except EmailNotExistError as e:
        logger.error(f"Email validation failed: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail=f"{str(e)}. Veuillez réessayer avec une adresse email correcte."
        )
    except Exception as e:
        logger.error(f"Email sending failed: {str(e)}")
        if "SMTP authentication failed" in str(e):
            raise HTTPException(
                status_code=500,
                detail="Erreur de configuration du serveur email. Veuillez contacter l'administrateur."
            )
        raise HTTPException(
            status_code=500,
            detail=f"Échec de l'envoi de l'email: {str(e)}. Veuillez réessayer."
        )

    # Store user data and code temporarily with expiration
    expires_at = datetime.now() + timedelta(minutes=CODE_EXPIRATION_MINUTES)
    pending_registrations[user_in.email] = {
        "code": code,
        "user_data": user_in.dict(),
        "expires_at": expires_at
    }

    return {"message": "Code de vérification envoyé par email"}

@router.post("/verify-registration", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def verify_registration(request: VerifyRegistrationRequest, db: Session = Depends(get_db), Authorize: AuthJWT = Depends()):
    email = request.email
    code = request.code

    # Check if the email exists in pending registrations
    if email not in pending_registrations:
        raise HTTPException(status_code=401, detail="Code invalide ou expiré")

    # Check if the code has expired
    if is_code_expired(pending_registrations[email]["expires_at"]):
        del pending_registrations[email]
        raise HTTPException(status_code=401, detail="Code invalide ou expiré")

    # Check if the code matches
    if pending_registrations[email]["code"] != code:
        raise HTTPException(status_code=401, detail="Code invalide ou expiré")

    # Retrieve user data
    user_data = pending_registrations[email]["user_data"]

    # Create user in the database
    user = User(
        email=user_data["email"],
        password_hash=pwd_context.hash(user_data["password"]),
        nom=user_data["nom"],
        prenom=user_data["prenom"],
        sexe=user_data["sexe"],
        date_naissance=user_data["date_naissance"]
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur de base de données: {str(e)}")

    # Generate tokens
    access_token = Authorize.create_access_token(subject=user.email, user_claims={"email": user.email})
    refresh_token = Authorize.create_refresh_token(subject=user.email, user_claims={"email": user.email})

    # Remove the pending registration
    del pending_registrations[email]

    return {
        "user": user,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/login", response_model=TokenResponse)
def login(login_data: LoginRequest, db: Session = Depends(get_db), Authorize: AuthJWT = Depends()):
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not pwd_context.verify(login_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")

    access_token = Authorize.create_access_token(subject=user.email, user_claims={"email": user.email})
    refresh_token = Authorize.create_refresh_token(subject=user.email, user_claims={"email": user.email})
    return {
        "user": user,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/refresh", response_model=TokenResponse)
def refresh(Authorize: AuthJWT = Depends(), db: Session = Depends(get_db)):
    Authorize.jwt_refresh_token_required()
    email = Authorize.get_jwt_subject()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    new_access_token = Authorize.create_access_token(subject=user.email, user_claims={"email": user.email})
    new_refresh_token = Authorize.create_refresh_token(subject=user.email, user_claims={"email": user.email})
    return {
        "user": user,
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }

@router.get("/me", response_model=UserResponse, dependencies=[Depends(security)])
def me(Authorize: AuthJWT = Depends(), db: Session = Depends(get_db)):
    Authorize.jwt_required()
    email = Authorize.get_jwt_subject()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    return user

@router.patch("/me", response_model=UserResponse, dependencies=[Depends(security)])
def update_profile(
    user_update: UserUpdate,
    Authorize: AuthJWT = Depends(),
    db: Session = Depends(get_db)
):
    Authorize.jwt_required()
    email = Authorize.get_jwt_subject()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    update_data = user_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    try:
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur de base de données: {str(e)}")

    return user

@router.post("/forgot-password")
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email non trouvé")

    code = generate_code()
    expires_at = datetime.now() + timedelta(minutes=CODE_EXPIRATION_MINUTES)
    pending_registrations[request.email] = {
        "code": code,
        "expires_at": expires_at
    }

    try:
        send_reset_code_email(to_email=user.email, code=code, reset_token="")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Échec de l'envoi de l'email: {str(e)}")

    return {"message": "Code de vérification envoyé par email"}

@router.post("/reset-password")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    email = request.email
    code = request.code

    if email not in pending_registrations:
        raise HTTPException(status_code=401, detail="Code invalide ou expiré")

    if is_code_expired(pending_registrations[email]["expires_at"]):
        del pending_registrations[email]
        raise HTTPException(status_code=401, detail="Code invalide ou expiré")

    if pending_registrations[email]["code"] != code:
        raise HTTPException(status_code=401, detail="Code invalide ou expiré")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    try:
        # Check if the User model has a set_password method; if not, use pwd_context directly
        if hasattr(user, 'set_password'):
            user.set_password(request.new_password)
        else:
            user.password_hash = pwd_context.hash(request.new_password)
        db.commit()
        del pending_registrations[email]
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur de base de données: {str(e)}")

    return {"message": "Mot de passe réinitialisé avec succès"}