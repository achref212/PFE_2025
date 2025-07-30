from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_jwt_auth import AuthJWT
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
from app.core.database import SessionLocal
from app.models.Location import Location
from app.models.Moyenne import Moyenne
from app.models.PlanAction import PlanAction, PlanStep, PlanQuestion, UserPlanResponse, UserStepAnswer
from app.models.user import User
from app.api.auth.schemas import (
    UserCreate, UserResponse, LoginRequest, TokenResponse, UserUpdate,
    ForgotPasswordRequest, VerifyCodeRequest, ResetPasswordRequest,
    VerifyRegistrationRequest, LocationCreate, LocationResponse,
    MoyenneCreate, MoyenneResponse, PlanActionCreate, PlanActionResponse,
    PlanStepCreate, PlanStepResponse, PlanQuestionCreate, PlanQuestionResponse,
    UserPlanResponseCreate, UserPlanResponseResponse, UserStepAnswerCreate, UserStepAnswerResponse,
    UserPlanUpdateRequest
)
from pydantic import BaseModel
from app.core.email import send_registration_code_email, send_reset_code_email, EmailNotExistError
from app.core.config import settings
from passlib.context import CryptContext
import random
import string
from typing import Dict
import re
import logging
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# In-memory storage for pending registrations (email -> {code, user_data, expires_at})
pending_registrations: Dict[str, dict] = {}
CODE_EXPIRATION_MINUTES = 30  # Codes expire after 30 minutes

class GoogleTokenRequest(BaseModel):
    token: str

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

# Email validation regex
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

def is_valid_email(email: str) -> bool:
    """Validate email format using regex and basic checks."""
    if not email or not isinstance(email, str):
        return False
    if not EMAIL_REGEX.match(email):
        return False
    return True

def validate_sexe(sexe: str) -> bool:
    """Validate sexe field to specific values."""
    valid_values = ["M", "F", "Other"]
    return sexe in valid_values

@router.post("/register", status_code=status.HTTP_202_ACCEPTED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """Register a new user and send verification code."""
    if not is_valid_email(user_in.email):
        raise HTTPException(
            status_code=400,
            detail="Format d'email invalide. Veuillez fournir une adresse email valide (exemple: user@example.com)."
        )

    if not validate_sexe(user_in.sexe):
        raise HTTPException(
            status_code=400,
            detail="Valeur invalide pour sexe. Valeurs autorisées: M, F, Other."
        )

    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=409, detail="Email déjà utilisé")

    code = generate_code()
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

    expires_at = datetime.now() + timedelta(minutes=CODE_EXPIRATION_MINUTES)
    pending_registrations[user_in.email] = {
        "code": code,
        "user_data": user_in.dict(),
        "expires_at": expires_at
    }

    return {"message": "Code de vérification envoyé par email"}

@router.post("/verify-registration", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def verify_registration(request: VerifyRegistrationRequest, db: Session = Depends(get_db), Authorize: AuthJWT = Depends()):
    """Verify registration code and create user."""
    email = request.email
    code = request.code

    if email not in pending_registrations:
        raise HTTPException(status_code=401, detail="Code invalide ou expiré")

    if is_code_expired(pending_registrations[email]["expires_at"]):
        del pending_registrations[email]
        raise HTTPException(status_code=401, detail="Code invalide ou expiré")

    if pending_registrations[email]["code"] != code:
        raise HTTPException(status_code=401, detail="Code invalide ou expiré")

    user_data = pending_registrations[email]["user_data"]
    user = User(
        email=user_data["email"],
        nom=user_data["nom"],
        prenom=user_data["prenom"],
        sexe=user_data["sexe"],
        date_naissance=user_data["date_naissance"]
    )
    user.set_password(user_data["password"])  # Use set_password method for validation

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        logger.error(f"Database error during registration: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur de base de données: {str(e)}")

    access_token = Authorize.create_access_token(subject=user.email, user_claims={"email": user.email})
    refresh_token = Authorize.create_refresh_token(subject=user.email, user_claims={"email": user.email})

    del pending_registrations[email]

    return {
        "user": user,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/login", response_model=TokenResponse)
def login(login_data: LoginRequest, db: Session = Depends(get_db), Authorize: AuthJWT = Depends()):
    """Authenticate user and return tokens."""
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not user.check_password(login_data.password):
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
    """Refresh access and refresh tokens."""
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

@router.get("/me", response_model=UserResponse)
def me(Authorize: AuthJWT = Depends(), db: Session = Depends(get_db)):
    """Get current user's profile."""
    Authorize.jwt_required()
    email = Authorize.get_jwt_subject()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    return user

@router.patch("/me", response_model=UserResponse)
def update_profile(
    user_update: UserUpdate,
    Authorize: AuthJWT = Depends(),
    db: Session = Depends(get_db)
):
    """Update current user's profile."""
    Authorize.jwt_required()
    email = Authorize.get_jwt_subject()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    update_data = user_update.dict(exclude_unset=True)
    logger.debug(f"Updating user {email} with fields: {update_data}")

    if "sexe" in update_data and not validate_sexe(update_data["sexe"]):
        raise HTTPException(
            status_code=400,
            detail="Valeur invalide pour sexe. Valeurs autorisées: M, F, Other."
        )

    for key, value in update_data.items():
        if hasattr(user, key):
            current_value = getattr(user, key)
            if current_value != value:
                logger.debug(f"Updating field {key}: {current_value} -> {value}")
                setattr(user, key, value)

    try:
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        logger.error(f"Database error during profile update: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la mise à jour du profil: {str(e)}")

    return user

@router.post("/forgot-password")
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Send password reset code."""
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
        logger.error(f"Email sending failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Échec de l'envoi de l'email: {str(e)}")

    return {"message": "Code de vérification envoyé par email"}

@router.post("/reset-password")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset user password with verification code."""
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
        user.set_password(request.new_password)
        db.commit()
        del pending_registrations[email]
    except Exception as e:
        db.rollback()
        logger.error(f"Database error during password reset: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur de base de données: {str(e)}")

    return {"message": "Mot de passe réinitialisé avec succès"}

@router.post("/auth/google", response_model=TokenResponse)
def google_login(
    token_data: GoogleTokenRequest,
    db: Session = Depends(get_db),
    Authorize: AuthJWT = Depends()
):
    """Authenticate user with Google OAuth."""
    try:
        idinfo = id_token.verify_oauth2_token(token_data.token, google_requests.Request())
        email = idinfo.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Email non trouvé dans le token Google")
        name = idinfo.get("name", "")
        picture = idinfo.get("picture", "")
        given_name = idinfo.get("given_name", "")
        family_name = idinfo.get("family_name", "")
    except ValueError as e:
        logger.error(f"Invalid Google token: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Token Google invalide: {str(e)}")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            nom=family_name or "Nom",
            prenom=given_name or "Prénom",
            sexe="Other",
            date_naissance=date(2000, 1, 1),
            password_hash=pwd_context.hash("google_login_" + email),
            profile_picture=picture
        )
        try:
            db.add(user)
            db.commit()
            db.refresh(user)
        except Exception as e:
            db.rollback()
            logger.error(f"Database error during Google user creation: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Erreur de base de données: {str(e)}")

    access_token = Authorize.create_access_token(subject=user.email, user_claims={"email": user.email})
    refresh_token = Authorize.create_refresh_token(subject=user.email, user_claims={"email": user.email})

    return {
        "user": user,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/me/location", response_model=UserResponse)
def update_location(
    location_data: LocationCreate,
    db: Session = Depends(get_db),
    Authorize: AuthJWT = Depends()
):
    """Create or update user's location."""
    Authorize.jwt_required()
    email = Authorize.get_jwt_subject()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    try:
        if user.location_id:
            location = db.query(Location).filter(Location.id == user.location_id).first()
            if not location:
                raise HTTPException(status_code=404, detail="Localisation introuvable")
            for key, value in location_data.dict().items():
                setattr(location, key, value)
        else:
            location = Location(**location_data.dict(), user_id=user.id)
            db.add(location)
            db.flush()
            user.location_id = location.id

        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        logger.error(f"Database error during location update: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la mise à jour de la localisation: {str(e)}")

    return user

@router.get("/me/location", response_model=LocationResponse)
def get_user_location(
    db: Session = Depends(get_db),
    Authorize: AuthJWT = Depends()
):
    """Get user's location."""
    Authorize.jwt_required()
    email = Authorize.get_jwt_subject()
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.location_id:
        raise HTTPException(status_code=404, detail="Localisation non trouvée")

    location = db.query(Location).filter(Location.id == user.location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Localisation introuvable")

    return location

@router.patch("/me/location", response_model=LocationResponse)
def update_user_location(
    location_data: LocationCreate,
    db: Session = Depends(get_db),
    Authorize: AuthJWT = Depends()
):
    """Update existing user's location."""
    Authorize.jwt_required()
    email = Authorize.get_jwt_subject()
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.location_id:
        raise HTTPException(status_code=404, detail="Localisation non trouvée")

    location = db.query(Location).filter(Location.id == user.location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Localisation introuvable")

    try:
        for key, value in location_data.dict().items():
            setattr(location, key, value)
        db.commit()
        db.refresh(location)
    except Exception as e:
        db.rollback()
        logger.error(f"Database error during location update: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la mise à jour de la localisation: {str(e)}")

    return location

@router.post("/me/moyenne", response_model=UserResponse)
def update_moyenne(
    moyenne_data: MoyenneCreate,
    db: Session = Depends(get_db),
    Authorize: AuthJWT = Depends()
):
    """Create or update user's grades."""
    Authorize.jwt_required()
    email = Authorize.get_jwt_subject()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    try:
        if user.moyenne_id:
            moyenne = db.query(Moyenne).filter(Moyenne.id == user.moyenne_id).first()
            if not moyenne:
                raise HTTPException(status_code=404, detail="Moyenne introuvable")
            for key, value in moyenne_data.dict().items():
                setattr(moyenne, f"moyenne_{key}" if key != "generale" else "moyenne_generale", value)
        else:
            moyenne = Moyenne(
                moyenne_generale=moyenne_data.generale,
                moyenne_francais=moyenne_data.francais,
                moyenne_philo=moyenne_data.philo,
                moyenne_math=moyenne_data.math,
                moyenne_svt=moyenne_data.svt,
                moyenne_physique=moyenne_data.physique,
                moyenne_anglais=moyenne_data.anglais,
                user_id=user.id
            )
            db.add(moyenne)
            db.flush()
            user.moyenne_id = moyenne.id

        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        logger.error(f"Database error during moyenne update: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la mise à jour des moyennes: {str(e)}")

    return user

@router.get("/me/moyenne", response_model=MoyenneResponse)
def get_user_moyenne(
    db: Session = Depends(get_db),
    Authorize: AuthJWT = Depends()
):
    """Get user's grades."""
    Authorize.jwt_required()
    email = Authorize.get_jwt_subject()
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.moyenne_id:
        raise HTTPException(status_code=404, detail="Moyenne non trouvée")

    moyenne = db.query(Moyenne).filter(Moyenne.id == user.moyenne_id).first()
    if not moyenne:
        raise HTTPException(status_code=404, detail="Moyenne introuvable")

    return moyenne

@router.patch("/me/moyenne", response_model=MoyenneResponse)
def update_user_moyenne(
    moyenne_data: MoyenneCreate,
    db: Session = Depends(get_db),
    Authorize: AuthJWT = Depends()
):
    """Update existing user's grades."""
    Authorize.jwt_required()
    email = Authorize.get_jwt_subject()
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.moyenne_id:
        raise HTTPException(status_code=404, detail="Moyenne non trouvée")

    moyenne = db.query(Moyenne).filter(Moyenne.id == user.moyenne_id).first()
    if not moyenne:
        raise HTTPException(status_code=404, detail="Moyenne introuvable")

    try:
        for key, value in moyenne_data.dict().items():
            setattr(moyenne, f"moyenne_{key}" if key != "generale" else "moyenne_generale", value)
        db.commit()
        db.refresh(moyenne)
    except Exception as e:
        db.rollback()
        logger.error(f"Database error during moyenne update: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la mise à jour des moyennes: {str(e)}")

    return moyenne

@router.post("/plan-action", response_model=PlanActionResponse)
def create_plan_action(
    plan_data: PlanActionCreate,
    db: Session = Depends(get_db),
    Authorize: AuthJWT = Depends()
):
    """Create a new plan action."""
    Authorize.jwt_required()
    email = Authorize.get_jwt_subject()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    try:
        plan = PlanAction(nom=plan_data.nom)
        db.add(plan)
        db.commit()
        db.refresh(plan)
    except Exception as e:
        db.rollback()
        logger.error(f"Database error during plan action creation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création du plan d'action: {str(e)}")

    return plan

@router.post("/plan-action/{plan_id}/step", response_model=PlanStepResponse)
def create_plan_step(
    plan_id: int,
    step_data: PlanStepCreate,
    db: Session = Depends(get_db),
    Authorize: AuthJWT = Depends()
):
    """Create a new step for a plan action."""
    Authorize.jwt_required()
    plan = db.query(PlanAction).filter(PlanAction.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan d'action non trouvé")

    try:
        step = PlanStep(titre=step_data.titre, plan_action_id=plan_id)
        db.add(step)
        db.commit()
        db.refresh(step)
    except Exception as e:
        db.rollback()
        logger.error(f"Database error during plan step creation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création de l'étape: {str(e)}")

    return step

@router.post("/plan-step/{step_id}/question", response_model=PlanQuestionResponse)
def create_plan_question(
    step_id: int,
    question_data: PlanQuestionCreate,
    db: Session = Depends(get_db),
    Authorize: AuthJWT = Depends()
):
    """Create a new question for a plan step."""
    Authorize.jwt_required()
    step = db.query(PlanStep).filter(PlanStep.id == step_id).first()
    if not step:
        raise HTTPException(status_code=404, detail="Étape non trouvée")

    try:
        question = PlanQuestion(contenu=question_data.contenu, step_id=step_id)
        db.add(question)
        db.commit()
        db.refresh(question)
    except Exception as e:
        db.rollback()
        logger.error(f"Database error during plan question creation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création de la question: {str(e)}")

    return question

@router.post("/me/plan-action/assign/{plan_id}", response_model=UserResponse)
def assign_plan_action(
    plan_id: int,
    db: Session = Depends(get_db),
    Authorize: AuthJWT = Depends()
):
    """Assign a plan action to the current user."""
    Authorize.jwt_required()
    email = Authorize.get_jwt_subject()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    plan = db.query(PlanAction).filter(PlanAction.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan d'action non trouvé")

    try:
        user.plan_action_id = plan_id
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        logger.error(f"Database error during plan action assignment: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'assignation du plan d'action: {str(e)}")

    return user

@router.post("/me/plan-response", response_model=UserResponse)
def submit_plan_response(
    response_data: UserPlanUpdateRequest,
    db: Session = Depends(get_db),
    Authorize: AuthJWT = Depends()
):
    """Submit or update user responses to plan questions."""
    Authorize.jwt_required()
    email = Authorize.get_jwt_subject()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    try:
        for response in response_data.reponses:
            question = db.query(PlanQuestion).filter(PlanQuestion.id == response.question_id).first()
            if not question:
                raise HTTPException(status_code=404, detail=f"Question {response.question_id} non trouvée")

            existing_response = db.query(UserPlanResponse).filter(
                UserPlanResponse.user_id == user.id,
                UserPlanResponse.question_id == response.question_id
            ).first()

            if existing_response:
                existing_response.reponse = response.reponse
            else:
                new_response = UserPlanResponse(
                    user_id=user.id,
                    question_id=response.question_id,
                    reponse=response.reponse
                )
                db.add(new_response)

        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        logger.error(f"Database error during plan response submission: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la soumission des réponses: {str(e)}")

    return user

@router.post("/me/step-answer", response_model=UserStepAnswerResponse)
def submit_step_answer(
    answer_data: UserStepAnswerCreate,
    db: Session = Depends(get_db),
    Authorize: AuthJWT = Depends()
):
    """Submit or update user answer to a plan step."""
    Authorize.jwt_required()
    email = Authorize.get_jwt_subject()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    step = db.query(PlanStep).filter(PlanStep.id == answer_data.step_id).first()
    if not step:
        raise HTTPException(status_code=404, detail="Étape non trouvée")

    try:
        existing_answer = db.query(UserStepAnswer).filter(
            UserStepAnswer.user_id == user.id,
            UserStepAnswer.step_id == answer_data.step_id
        ).first()

        if existing_answer:
            existing_answer.response = answer_data.response
        else:
            new_answer = UserStepAnswer(
                user_id=user.id,
                step_id=answer_data.step_id,
                response=answer_data.response
            )
            db.add(new_answer)

        db.commit()
        db.refresh(existing_answer if existing_answer else new_answer)
    except Exception as e:
        db.rollback()
        logger.error(f"Database error during step answer submission: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la soumission de la réponse: {str(e)}")

    return existing_answer if existing_answer else new_answer

@router.get("/me/plan-action", response_model=PlanActionResponse)
def get_user_plan_action(
    db: Session = Depends(get_db),
    Authorize: AuthJWT = Depends()
):
    """Get user's assigned plan action with steps, questions, and responses."""
    Authorize.jwt_required()
    email = Authorize.get_jwt_subject()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    if not user.plan_action_id:
        raise HTTPException(status_code=404, detail="Plan d’action non assigné")

    plan = db.query(PlanAction).filter(PlanAction.id == user.plan_action_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan d’action non trouvé")

    return plan