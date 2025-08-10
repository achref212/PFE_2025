import re

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_jwt_auth import AuthJWT
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session, lazyload, selectinload
from sqlalchemy import func, asc
from datetime import datetime, timedelta, date
import random
import string
import logging
from typing import Dict, List, Optional

from pydantic import BaseModel

from app.api.formation.schemas import AcademieSchema, LieuSchema, EtablissementSchema, FormationSchema, AcademieOut, \
    EtablissementOut
# --- Core / DB ---
from app.core.database import SessionLocal
from app.core.email import (
    send_registration_code_email,
    send_reset_code_email,
    EmailNotExistError,
)
from passlib.context import CryptContext

from app.models.Academies import Academie, Etablissement
# --- Models ---
from app.models.user import User
from app.models.PlanAction import PlanAction, PlanStep, UserStepProgress
from app.models.Formation import Formation, CriteresCandidature, Lieu  # keep your formation model

# --- Schemas (your updated file we aligned earlier) ---
from app.api.auth.schemas import (
    # Auth / user
    UserCreate, UserResponse, LoginRequest, TokenResponse, UserUpdate,
    ForgotPasswordRequest, VerifyCodeRequest, ResetPasswordRequest, VerifyRegistrationRequest,
    # Plan
    PlanActionCreate, PlanActionResponse,
    PlanStepCreate, PlanStepResponse,
    UserStepProgressCreate, UserStepProgressUpdate, UserStepProgressResponse,
)

# --- Google ---
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
def bootstrap_user_plan(db: Session, user: User) -> PlanAction:
    """
    Create a default PlanAction + 6 PlanSteps for the user and initialize UserStepProgress.
    Safe to call multiple times: it won't create a new plan if user already has one.
    """
    if user.plan_action_id:
        # User already has a plan assigned
        plan = db.query(PlanAction).filter(PlanAction.id == user.plan_action_id).first()
        if plan:
            return plan

    today = datetime.utcnow().date()
    plan = PlanAction(
        nom=f"Plan d’action de {user.prenom or user.nom or user.email}",
        start_date=today,
        end_date=today + timedelta(days=30),
        is_active=True,
    )
    db.add(plan)
    db.flush()  # to get plan.id

    steps_spec = [
        ("mes infos de base", "Complète tes infos personnelles de base."),
        ("définir mes préférences", "Choisis tes domaines et types de formation préférés."),
        ("commencer l’exploration de formations", "Parcours des formations pertinentes."),
        ("identifier mes intérêts professionnels", "Fais des tests et clarifie tes intérêts."),
        ("explorer mes formations (2/2)", "Approfondis les formations déjà repérées."),
        ("commencer ma liste de formations favorites", "Ajoute tes options favorites à suivre."),
    ]

    for idx, (titre, description) in enumerate(steps_spec, start=1):
        step_start = today + timedelta(days=7 * (idx - 1))
        step_end = step_start + timedelta(days=14)
        step = PlanStep(
            plan_action_id=plan.id,
            titre=titre,
            description=description,
            ordre=idx,
            start_date=step_start,
            end_date=step_end,
        )
        db.add(step)
        db.flush()  # to get step.id

        progress = UserStepProgress(
            user_id=user.id,
            step_id=step.id,
            is_done=False,
            done_at=None,
        )
        db.add(progress)

    user.plan_action_id = plan.id
    db.commit()
    db.refresh(plan)
    db.refresh(user)
    return plan

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
        # 🔥 Create plan/steps/progress
        bootstrap_user_plan(db, user)
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
    Authorize: AuthJWT = Depends(),
):
    """Authenticate with Google and hydrate user with picture / gender / birthdate / address (if present)."""
    try:
        idinfo = id_token.verify_oauth2_token(token_data.token, google_requests.Request())
    except ValueError as e:
        logger.error(f"Invalid Google token: {e}")
        raise HTTPException(status_code=401, detail="Token Google invalide")

    email = idinfo.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email non trouvé dans le token Google")
    email = email.lower()

    given_name = idinfo.get("given_name") or ""
    family_name = idinfo.get("family_name") or ""
    picture = idinfo.get("picture") or None
    gender = idinfo.get("gender")
    birthdate = idinfo.get("birthdate")

    # OpenID 'address' claim (dict or string)
    adresse = None
    addr_claim = idinfo.get("address")
    if isinstance(addr_claim, dict):
        adresse = addr_claim.get("formatted") or " ".join(
            filter(
                None,
                [
                    addr_claim.get("street_address"),
                    addr_claim.get("locality"),
                    addr_claim.get("region"),
                    addr_claim.get("postal_code"),
                    addr_claim.get("country"),
                ],
            )
        ).strip() or None
    elif isinstance(addr_claim, str):
        adresse = addr_claim.strip() or None

    def map_gender_to_sexe(g: Optional[str]) -> str:
        if not g:
            return "M"
        g = g.lower()
        if g == "male":
            return "M"
        if g == "female":
            return "F"
        return "O"

    def parse_birthdate(b: str) -> date:
        try:
            return datetime.strptime(b, "%Y-%m-%d").date()
        except Exception:
            logger.warning(f"Invalid birthdate from Google: {b}")
            return date(2000, 1, 1)

    # Upsert user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            nom=family_name or "Nom",
            prenom=given_name or "Prénom",
            sexe=map_gender_to_sexe(gender),
            date_naissance=parse_birthdate(birthdate) if birthdate else date(2000, 1, 1),
            password_hash=pwd_context.hash("google_login_" + email),
            profile_picture=picture,
            # Optional user profile fields:
            objectif=None,
            niveau_scolaire=None,
            voie=None,
            specialites=None,
            filiere=None,
            telephone=None,
            budget=None,
            est_boursier=False,
            # Address/geo fields on User (nullable)
            adresse=adresse or None,
            distance=None,
            latitude=None,
            longitude=None,
            etablissement=None,
            academie=None,
        )
        try:
            db.add(user)
            db.commit()
            db.refresh(user)
            bootstrap_user_plan(db, user)
        except Exception as e:
            db.rollback()
            logger.error(f"DB error during Google user creation: {e}")
            raise HTTPException(status_code=500, detail="Erreur de base de données")
    else:
        changed = False
        if not user.profile_picture and picture:
            user.profile_picture = picture
            changed = True
        if not user.adresse and adresse:
            user.adresse = adresse
            changed = True
        if user.date_naissance == date(2000, 1, 1) and birthdate:
            user.date_naissance = parse_birthdate(birthdate)
            changed = True
        if (not user.sexe or user.sexe not in {"M", "F", "O"}) and gender:
            user.sexe = map_gender_to_sexe(gender)
            changed = True
        if changed:
            try:
                db.commit()
                db.refresh(user)
            except Exception as e:
                db.rollback()
                logger.error(f"DB error during Google user update: {e}")
                raise HTTPException(status_code=500, detail="Erreur de base de données")

    access_token = Authorize.create_access_token(subject=user.email)
    refresh_token = Authorize.create_refresh_token(subject=user.email)
    return {"user": user, "access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

# =========================
# Plan Actions & Steps
# =========================

@router.post("/plans", response_model=PlanActionResponse, status_code=201)
def create_plan(
    payload: PlanActionCreate,
    db: Session = Depends(get_db),
    Authorize: AuthJWT = Depends(),
):
    Authorize.jwt_required()
    plan = PlanAction(
        nom=payload.nom,
        start_date=payload.start_date,
        end_date=payload.end_date,
        is_active=payload.is_active if payload.is_active is not None else True,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan

@router.get("/plans/{plan_id}", response_model=PlanActionResponse)
def get_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    Authorize: AuthJWT = Depends(),
):
    Authorize.jwt_required()
    plan = (
        db.query(PlanAction)
        .options(selectinload(PlanAction.steps))
        .filter(PlanAction.id == plan_id)
        .first()
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Plan d’action non trouvé")
    return plan

@router.post("/plans/{plan_id}/steps", response_model=PlanStepResponse, status_code=201)
def create_plan_step(
    plan_id: int,
    payload: PlanStepCreate,
    db: Session = Depends(get_db),
    Authorize: AuthJWT = Depends(),
):
    Authorize.jwt_required()
    plan = db.query(PlanAction).filter(PlanAction.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan d’action non trouvé")

    step = PlanStep(
        plan_action_id=plan_id,
        titre=payload.titre,
        description=payload.description,
        ordre=payload.ordre,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    return step

@router.post("/users/{user_id}/assign-plan/{plan_id}", response_model=UserResponse)
def assign_plan_to_user(
    user_id: int,
    plan_id: int,
    db: Session = Depends(get_db),
    Authorize: AuthJWT = Depends(),
):
    Authorize.jwt_required()
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    plan = db.query(PlanAction).filter(PlanAction.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan d’action non trouvé")

    user.plan_action_id = plan.id
    db.commit()
    db.refresh(user)
    return user

@router.get("/me/plan-action", response_model=PlanActionResponse)
def get_user_plan_action(
    db: Session = Depends(get_db),
    Authorize: AuthJWT = Depends(),
):
    """Return my assigned plan with ordered steps."""
    Authorize.jwt_required()
    email = Authorize.get_jwt_subject()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    if not user.plan_action_id:
        raise HTTPException(status_code=404, detail="Plan d’action non assigné")

    plan = (
        db.query(PlanAction)
        .options(selectinload(PlanAction.steps))
        .filter(PlanAction.id == user.plan_action_id)
        .first()
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Plan d’action non trouvé")
    return plan

# =========================
# User Step Progress
# =========================

@router.post("/users/{user_id}/steps/{step_id}/done", response_model=UserStepProgressResponse, status_code=201)
def mark_step_done(
    user_id: int,
    step_id: int,
    payload: UserStepProgressCreate,
    db: Session = Depends(get_db),
    Authorize: AuthJWT = Depends(),
):
    Authorize.jwt_required()
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    step = db.query(PlanStep).filter(PlanStep.id == step_id).first()
    if not step:
        raise HTTPException(status_code=404, detail="Étape non trouvée")

    progress = (
        db.query(UserStepProgress)
        .filter(UserStepProgress.user_id == user_id, UserStepProgress.step_id == step_id)
        .first()
    )
    now = datetime.utcnow()
    if progress:
        progress.is_done = True
        progress.done_at = now
    else:
        progress = UserStepProgress(user_id=user_id, step_id=step_id, is_done=True, done_at=now)
        db.add(progress)
    db.commit()
    db.refresh(progress)
    return progress

@router.patch("/users/{user_id}/steps/{step_id}", response_model=UserStepProgressResponse)
def update_step_progress(
    user_id: int,
    step_id: int,
    payload: UserStepProgressUpdate,
    db: Session = Depends(get_db),
    Authorize: AuthJWT = Depends(),
):
    Authorize.jwt_required()
    progress = (
        db.query(UserStepProgress)
        .filter(UserStepProgress.user_id == user_id, UserStepProgress.step_id == step_id)
        .first()
    )
    if not progress:
        raise HTTPException(status_code=404, detail="Progression introuvable")

    progress.is_done = payload.is_done
    progress.done_at = datetime.utcnow() if payload.is_done else None
    db.commit()
    db.refresh(progress)
    return progress

@router.get("/users/{user_id}/progress", response_model=List[UserStepProgressResponse])
def list_user_progress(
    user_id: int,
    db: Session = Depends(get_db),
    Authorize: AuthJWT = Depends(),
):
    Authorize.jwt_required()
    progress = (
        db.query(UserStepProgress)
        .filter(UserStepProgress.user_id == user_id)
        .all()
    )
    return progress


# Get a specific formation with all details



@router.get("/formations/{formation_id}", response_model=FormationSchema)
def get_formation(formation_id: int, db: Session = Depends(get_db)):
    # Use lazyload('*') to defer all relationship loading
    formation = db.query(Formation).options(
        lazyload('*')  # Defer loading of all relationships
    ).filter(Formation.id == formation_id).first()

    if not formation:
        raise HTTPException(status_code=404, detail="Formation not found")

    # Force loading of relationships to ensure all data is available for serialization
    formation.lieu  # Accessing triggers lazy load
    formation.salaire_bornes
    formation.badges  # Accessing collections triggers lazy load
    formation.filieres_bac
    formation.specialites_favorisees
    formation.matieres_enseignees
    formation.debouches_metiers
    formation.debouches_secteurs
    formation.ts_taux_par_bac
    formation.intervalles_admis
    formation.profils_admis
    formation.criteres_candidature  # Includes sous_criteres due to relationship
    formation.boursiers
    formation.promo_characteristics
    formation.post_formation_outcomes
    formation.voie_generale
    formation.voie_pro
    formation.voie_technologique

    return formation




# Get a specific formation with all details

@router.get("/formations/voie_technologique", response_model=List[FormationSchema])
def get_formations_voie_technologique(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    formations = db.query(Formation).filter(Formation.voie_technologique != None).offset(skip).limit(limit).all()

    if not formations:
        raise HTTPException(status_code=404, detail="Aucune formation voie technologique trouvée.")

    return formations


@router.get("/formations/{formation_id}", response_model=FormationSchema)
def get_formation(formation_id: int, db: Session = Depends(get_db)):
    # Use lazyload('*') to defer all relationship loading
    formation = db.query(Formation).options(
        lazyload('*')  # Defer loading of all relationships
    ).filter(Formation.id == formation_id).first()

    if not formation:
        raise HTTPException(status_code=404, detail="Formation not found")

    # Force loading of relationships to ensure all data is available for serialization
    formation.lieu  # Accessing triggers lazy load
    formation.salaire_bornes
    formation.badges  # Accessing collections triggers lazy load
    formation.filieres_bac
    formation.specialites_favorisees
    formation.matieres_enseignees
    formation.debouches_metiers
    formation.debouches_secteurs
    formation.ts_taux_par_bac
    formation.intervalles_admis
    formation.profils_admis
    formation.criteres_candidature  # Includes sous_criteres due to relationship
    formation.boursiers
    formation.promo_characteristics
    formation.post_formation_outcomes
    formation.voie_generale
    formation.voie_pro
    formation.voie_technologique

    return formation

# Get 10 formations
@router.get("/formations/", response_model=List[FormationSchema])
def get_formations(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    limit = min(limit, 10)

    try:
        formations = db.query(Formation).options(
            lazyload('*'),  # Pour éviter les accès indésirables
            selectinload(Formation.lieu),
            selectinload(Formation.salaire_bornes),
            selectinload(Formation.badges),
            selectinload(Formation.filieres_bac),
            selectinload(Formation.specialites_favorisees),
            selectinload(Formation.matieres_enseignees),
            selectinload(Formation.debouches_metiers),
            selectinload(Formation.debouches_secteurs),
            selectinload(Formation.ts_taux_par_bac),
            selectinload(Formation.intervalles_admis),
            selectinload(Formation.criteres_candidature).selectinload(CriteresCandidature.sous_criteres),
            selectinload(Formation.boursiers),
            selectinload(Formation.profils_admis),
            selectinload(Formation.promo_characteristics),
            selectinload(Formation.post_formation_outcomes),
            selectinload(Formation.voie_generale),
            selectinload(Formation.voie_pro),
            selectinload(Formation.voie_technologique)
        ).offset(skip).limit(limit).all()

        return formations

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur lors du chargement des formations: {str(e)}")
# Updated route to get etablissements
@router.get("/etablissements/", response_model=List[EtablissementSchema])
def get_etablissements(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    limit = min(limit, 10)  # Cap limit to prevent overload

    # Fetch establishments from Formation.lieu and Location
    etab_from_formation = db.query(Formation.etablissement).distinct().filter(
        Formation.etablissement.isnot(None)
    ).subquery()

    etab_from_location = db.query(Formation.etablissement).distinct().filter(
        Formation.etablissement.isnot(None)
    ).subquery()

    all_etablissements = db.query(
        func.coalesce(etab_from_formation.c.etablissement, etab_from_location.c.etablissement)).distinct().all()

    # Paginate the results
    start = skip
    end = min(skip + limit, len(all_etablissements))
    paginated_etablissements = all_etablissements[start:end]

    # Create EtablissementSchema objects with a default description
    result = [
        EtablissementSchema(name=etab[0], description=f"Établissement à {etab[0]}")
        for etab in paginated_etablissements
    ]
    return result


# Updated route to get academies on lieu
@router.get("/lieu/academies/", response_model=List[AcademieSchema])
def get_academies(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    limit = min(limit, 10)  # Cap limit to prevent overload

    # Fetch academies from Formation.lieu and Location
    acad_from_formation = db.query(Formation.lieu.of_type(LieuSchema).academy).distinct().filter(
        Formation.lieu.has(LieuSchema.academy.isnot(None))
    ).subquery()

    acad_from_location = db.query(Lieu.academie).distinct().filter(
        Lieu.academie.isnot(None)
    ).subquery()

    all_academies = db.query(
        func.coalesce(acad_from_formation.c.academy, acad_from_location.c.academie)).distinct().all()

    # Paginate the results
    start = skip
    end = min(skip + limit, len(all_academies))
    paginated_academies = all_academies[start:end]

    # Create AcademieSchema objects
    result = [
        AcademieSchema(name=acad[0])
        for acad in paginated_academies
    ]
    return result

@router.get("/academies", response_model=List[AcademieOut])
def list_academies(
    q: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Academie)
    if q:
        query = query.filter(Academie.name.ilike(f"%{q}%"))
    rows = query.order_by(asc(Academie.name)).all()
    return [AcademieOut(id=a.id, name=a.name) for a in rows]

@router.get("/academies/{academie_id}", response_model=AcademieOut)
def get_academie(
    academie_id: int,
    with_etablissements: bool = True,
    db: Session = Depends(get_db),
):
    query = db.query(Academie)
    if with_etablissements:
        query = query.options(selectinload(Academie.etablissements))
    a = query.filter(Academie.id == academie_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Académie non trouvée")

    return AcademieOut(
        id=a.id,
        name=a.name,
        etablissements=[
            EtablissementOut(
                id=e.id,
                academie_id=e.academie_id,
                etablissement=e.etablissement,
                city=e.city,
                sector=e.sector,
                track=e.track,
            ) for e in (a.etablissements or [])
        ] if with_etablissements else None
    )

@router.get("/academies/{academie_id}/etablissements", response_model=List[EtablissementOut])
def list_etablissements_in_academie(
    academie_id: int,
    q: Optional[str] = None,
    city: Optional[str] = None,
    track: Optional[str] = None,
    sector: Optional[str] = None,
    db: Session = Depends(get_db),
):
    exists = db.query(Academie.id).filter(Academie.id == academie_id).first()
    if not exists:
        raise HTTPException(status_code=404, detail="Académie non trouvée")

    base = db.query(Etablissement).filter(Etablissement.academie_id == academie_id)
    if q:
        base = base.filter(Etablissement.etablissement.ilike(f"%{q}%"))
    if city:
        base = base.filter(Etablissement.city.ilike(f"%{city}%"))
    if track:
        base = base.filter(Etablissement.track.ilike(f"%{track}%"))
    if sector:
        base = base.filter(Etablissement.sector.ilike(f"%{sector}%"))

    rows = base.order_by(asc(Etablissement.etablissement), asc(Etablissement.city)).all()
    return [
        EtablissementOut(
            id=e.id,
            academie_id=e.academie_id,
            etablissement=e.etablissement,
            city=e.city,
            sector=e.sector,
            track=e.track,
        ) for e in rows
    ]

@router.get("/etablissements", response_model=List[EtablissementOut])
def list_etablissements(
    q: Optional[str] = None,
    academie_id: Optional[int] = None,
    city: Optional[str] = None,
    track: Optional[str] = None,
    sector: Optional[str] = None,
    db: Session = Depends(get_db),
):
    base = db.query(Etablissement)

    if academie_id is not None:
        base = base.filter(Etablissement.academie_id == academie_id)
    if q:
        base = base.filter(Etablissement.etablissement.ilike(f"%{q}%"))
    if city:
        base = base.filter(Etablissement.city.ilike(f"%{city}%"))
    if track:
        base = base.filter(Etablissement.track.ilike(f"%{track}%"))
    if sector:
        base = base.filter(Etablissement.sector.ilike(f"%{sector}%"))

    rows = base.order_by(asc(Etablissement.etablissement), asc(Etablissement.city)).all()
    return [
        EtablissementOut(
            id=e.id,
            academie_id=e.academie_id,
            etablissement=e.etablissement,
            city=e.city,
            sector=e.sector,
            track=e.track,
        ) for e in rows
    ]

@router.get("/etablissements/{etablissement_id}", response_model=EtablissementOut)
def get_etablissement(
    etablissement_id: int,
    db: Session = Depends(get_db),
):
    e = (
        db.query(Etablissement)
        .options(selectinload(Etablissement.academie))
        .filter(Etablissement.id == etablissement_id)
        .first()
    )
    if not e:
        raise HTTPException(status_code=404, detail="Établissement non trouvé")

    return EtablissementOut(
        id=e.id,
        academie_id=e.academie_id,
        etablissement=e.etablissement,
        city=e.city,
        sector=e.sector,
        track=e.track,
    )