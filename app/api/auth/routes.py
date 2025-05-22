from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_jwt_auth import AuthJWT
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.core.database import SessionLocal
from app.models.user import User, pwd_context
from app.api.auth.schemas import (
    UserCreate, UserResponse, LoginRequest, TokenResponse, UserUpdate,
    ForgotPasswordRequest, VerifyCodeRequest, ResetPasswordRequest, VerifyRegistrationRequest
)
from app.core.email import send_reset_code_email, send_registration_code_email
from app.core.config import settings
import random
import string
router = APIRouter()
security = HTTPBearer()
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
def generate_code(length=6):
    return ''.join(random.choices(string.digits, k=length))

@router.post("/register", status_code=status.HTTP_202_ACCEPTED)
def register(user_in: UserCreate, db: Session = Depends(get_db), Authorize: AuthJWT = Depends()):
    # Check if email already exists
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=409, detail="Email déjà utilisé")

    # Generate 6-digit code
    code = generate_code()

    # Hash password
    password_hash = pwd_context.hash(user_in.password)

    # Create JWT token with user data and code
    verification_token = Authorize.create_access_token(
        subject=user_in.email,
        user_claims={
            "code": code,
            "scope": "registration_verification",
            "password_hash": password_hash,
            "nom": user_in.nom,
            "prenom": user_in.prenom,
            "sexe": user_in.sexe,
            "date_naissance": user_in.date_naissance.isoformat()
        },
        expires_time=settings.REGISTRATION_CODE_EXPIRES
    )

    # Send verification email
    try:
        send_registration_code_email(to_email=user_in.email, code=code, verification_token=verification_token)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Adresse email invalide. Veuillez fournir une adresse email correcte: {str(e)}"
        )

    return {"message": "Code de vérification envoyé par email"}

@router.post("/verify-registration", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def verify_registration(request: VerifyRegistrationRequest, db: Session = Depends(get_db), Authorize: AuthJWT = Depends()):
    try:
        Authorize.set_access_cookies(request.token)
        Authorize.jwt_required()
        claims = Authorize.get_raw_jwt()
        if claims.get("scope") != "registration_verification":
            raise HTTPException(status_code=401, detail="Invalid token scope")
        if claims.get("code") != request.code:
            raise HTTPException(status_code=401, detail="Code invalide")
        email = Authorize.get_jwt_subject()
        if email != request.email:
            raise HTTPException(status_code=401, detail="Invalid email")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Code invalide ou expiré")

    # Check if user already exists
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="Email déjà utilisé")

    # Create user from JWT claims
    user = User(
        email=email,
        password_hash=claims["password_hash"],
        nom=claims["nom"],
        prenom=claims["prenom"],
        sexe=claims["sexe"],
        date_naissance=datetime.fromisoformat(claims["date_naissance"]).date()
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/login", response_model=TokenResponse)
def login(login_data: LoginRequest, db: Session = Depends(get_db), Authorize: AuthJWT = Depends()):
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not user.check_password(login_data.password):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")

    access_token = Authorize.create_access_token(subject=user.email, user_claims={"email": user.email})
    return {
        "user": user,
        "access_token": access_token,
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

    # Update fields that are provided
    update_data = user_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    try:
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return user

@router.post("/forgot-password")
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db), Authorize: AuthJWT = Depends()):
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email non trouvé")

    # Generate 6-digit code
    code = generate_code()

    # Create JWT token with code
    reset_token = Authorize.create_access_token(
        subject=user.email,
        user_claims={"code": code, "scope": "password_reset"},
        expires_time=settings.RESET_CODE_EXPIRES
    )

    # Send email with code
    try:
        send_reset_code_email(to_email=user.email, code=code, reset_token=reset_token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

    return {"message": "Code de vérification envoyé par email"}

@router.post("/verify-code")
def verify_code(request: VerifyCodeRequest, db: Session = Depends(get_db), Authorize: AuthJWT = Depends()):
    try:
        Authorize.set_access_cookies(request.token)
        Authorize.jwt_required()
        claims = Authorize.get_raw_jwt()
        if claims.get("scope") != "password_reset":
            raise HTTPException(status_code=401, detail="Invalid token scope")
        email = Authorize.get_jwt_subject()
        if email != request.email:
            raise HTTPException(status_code=401, detail="Invalid email")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return {"message": "Code vérifié avec succès"}

@router.post("/reset-password")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db), Authorize: AuthJWT = Depends()):
    try:
        Authorize.set_access_cookies(request.token)
        Authorize.jwt_required()
        claims = Authorize.get_raw_jwt()
        if claims.get("scope") != "password_reset":
            raise HTTPException(status_code=401, detail="Invalid token scope")
        email = Authorize.get_jwt_subject()
        if email != request.email:
            raise HTTPException(status_code=401, detail="Invalid email")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    try:
        user.set_password(request.new_password)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return {"message": "Mot de passe réinitialisé avec succès"}