# app/api/auth/routes.py
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.formation.schemas import FormationSchema
from app.core.database import SessionLocal, engine
from app.models.Formation import Formation, Lieu, SalaireBornes, Badge, FiliereBac, SpecialiteFavorisee, MatiereEnseignee, DeboucheMetier, DeboucheSecteur, TsTauxParBac, IntervalsAdmis, CriteresCandidature, SousCritere, Boursiers, ProfilsAdmis, PromoCharacteristics, PostFormationOutcomes, VoieGenerale, VoiePro, VoieTechnologique
router = APIRouter()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Get a specific formation with all details
@router.get("/formations/{formation_id}", response_model=FormationSchema)
def get_formation(formation_id: int, db: Session = Depends(get_db)):
    formation = db.query(Formation).filter(Formation.id == formation_id).first()
    if not formation:
        raise HTTPException(status_code=404, detail="Formation not found")

    result = {
        "id": formation.id,
        "timestamp": formation.timestamp,
        "url": formation.url,
        "titre": formation.titre,
        "etablissement": formation.etablissement,
        "type_formation": formation.type_formation,
        "type_etablissement": formation.type_etablissement,
        "formation_controlee_par_etat": formation.formation_controlee_par_etat,
        "apprentissage": formation.apprentissage,
        "prix_annuel": formation.prix_annuel,
        "salaire_moyen": formation.salaire_moyen,
        "poursuite_etudes": formation.poursuite_etudes,
        "taux_insertion": formation.taux_insertion,
        "lien_onisep": formation.lien_onisep,
        "resume_programme": formation.resume_programme,
        "duree": formation.duree,
        "formation_selective": formation.formation_selective,
        "taux_passage_2e_annee": formation.taux_passage_2e_annee,
        "acces_formation": formation.acces_formation,
        "pre_bac_admission_percentage": formation.pre_bac_admission_percentage,
        "female_percentage": formation.female_percentage,
        "new_bac_students_count": formation.new_bac_students_count,
        "total_admitted_count": formation.total_admitted_count,
        "complementary_phase_acceptance_percentage": formation.complementary_phase_acceptance_percentage,
        "taux_reussite_3_4_ans": formation.taux_reussite_3_4_ans,
        "lieu": db.query(Lieu).filter(Lieu.formation_id == formation_id).first(),
        "salaire_bornes": db.query(SalaireBornes).filter(SalaireBornes.formation_id == formation_id).first(),
        "badges": db.query(Badge).filter(Badge.formation_id == formation_id).all(),
        "filieres_bac": db.query(FiliereBac).filter(FiliereBac.formation_id == formation_id).all(),
        "specialites_favorisees": db.query(SpecialiteFavorisee).filter(SpecialiteFavorisee.formation_id == formation_id).all(),
        "matieres_enseignees": db.query(MatiereEnseignee).filter(MatiereEnseignee.formation_id == formation_id).all(),
        "debouches_metiers": db.query(DeboucheMetier).filter(DeboucheMetier.formation_id == formation_id).all(),
        "debouches_secteurs": db.query(DeboucheSecteur).filter(DeboucheSecteur.formation_id == formation_id).all(),
        "ts_taux_par_bac": db.query(TsTauxParBac).filter(TsTauxParBac.formation_id == formation_id).all(),
        "intervalles_admis": db.query(IntervalsAdmis).filter(IntervalsAdmis.formation_id == formation_id).all(),
        "criteres_candidature": db.query(CriteresCandidature).filter(CriteresCandidature.formation_id == formation_id).all(),
        "boursiers": db.query(Boursiers).filter(Boursiers.formation_id == formation_id).first(),
        "profils_admis": db.query(ProfilsAdmis).filter(ProfilsAdmis.formation_id == formation_id).all(),
        "promo_characteristics": db.query(PromoCharacteristics).filter(PromoCharacteristics.formation_id == formation_id).first(),
        "post_formation_outcomes": db.query(PostFormationOutcomes).filter(PostFormationOutcomes.formation_id == formation_id).first(),
        "voie_generale": db.query(VoieGenerale).filter(VoieGenerale.formation_id == formation_id).first(),
        "voie_pro": db.query(VoiePro).filter(VoiePro.formation_id == formation_id).first(),
        "voie_technologique": db.query(VoieTechnologique).filter(VoieTechnologique.formation_id == formation_id).first()
    }
    return result

# Get 10 formations
@router.get("/formations/", response_model=List[FormationSchema])
def get_formations(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    formations = db.query(Formation).offset(skip).limit(limit).all()
    return formations