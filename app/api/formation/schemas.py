# app/api/auth/schemas.py
import json
from pydantic import BaseModel, validator

from pydantic import BaseModel
from typing import List, Optional
# Pydantic schemas
class EtablissementSchema(BaseModel):
    name: str
    description: str

    class Config:
        orm_mode = True

class AcademieSchema(BaseModel):
    name: str

    class Config:
        orm_mode = True
class LieuSchema(BaseModel):
    ville: str
    region: str
    departement: str
    academy: str
    gps_coordinates: str

    class Config:
        orm_mode = True

class SalaireBornesSchema(BaseModel):
    min: float
    max: float

    class Config:
        orm_mode = True

class BadgeSchema(BaseModel):
    badge: str

    class Config:
        orm_mode = True

class FiliereBacSchema(BaseModel):
    filiere: str

    class Config:
        orm_mode = True

class SpecialiteFavoriseeSchema(BaseModel):
    specialite: str

    class Config:
        orm_mode = True

class MatiereEnseigneeSchema(BaseModel):
    matiere: str

    class Config:
        orm_mode = True

class DeboucheMetierSchema(BaseModel):
    metier: str

    class Config:
        orm_mode = True

class DeboucheSecteurSchema(BaseModel):
    secteur: str

    class Config:
        orm_mode = True

class TsTauxParBacSchema(BaseModel):
    bac_type: str
    taux: str

    class Config:
        orm_mode = True

class IntervalsAdmisSchema(BaseModel):
    interval_type: str
    tle_generale: str
    tle_techno: str
    tle_pro: str

    class Config:
        orm_mode = True

class SousCritereSchema(BaseModel):
    type: str
    titre: str
    description: str

    class Config:
        orm_mode = True

class CriteresCandidatureSchema(BaseModel):
    categorie: str
    poids: float
    sous_criteres: List[SousCritereSchema] = []

    class Config:
        orm_mode = True

class BoursiersSchema(BaseModel):
    taux_minimum_boursiers: str
    pourcentage_boursiers_neo_bacheliers: float

    class Config:
        orm_mode = True

class ProfilsAdmisSchema(BaseModel):
    bac_type: str
    percentage: float

    class Config:
        orm_mode = True

class PromoCharacteristicsSchema(BaseModel):
    new_bac_students_count: int
    female_percentage: float
    total_admitted_count: int

    class Config:
        orm_mode = True

class PostFormationOutcomesSchema(BaseModel):
    poursuivent_etudes: str
    en_emploi: str
    autre_situation: str

    class Config:
        orm_mode = True

class VoieSchema(BaseModel):
    filieres: List[str] = []
    specialities: List[str] = []

    @validator("filieres", pre=True)
    def parse_filieres(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except:
                return []
        elif isinstance(v, list):
            return v
        return []

    @validator("specialities", pre=True)
    def parse_specialities(cls, v):
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                # Si c’est un dict (comme {"ST2S": [...]}) → on prend les valeurs
                if isinstance(parsed, dict):
                    values = []
                    for arr in parsed.values():
                        if isinstance(arr, list):
                            values.extend(arr)
                    return values
                elif isinstance(parsed, list):
                    return parsed
                return []
            except:
                return []
        elif isinstance(v, list):
            return v
        return []

    class Config:
        orm_mode = True

class FormationSchema(BaseModel):
    id: int
    timestamp: str
    url: str
    titre: str
    etablissement: str
    type_formation: str
    type_etablissement: str
    formation_controlee_par_etat: bool
    apprentissage: str
    prix_annuel: Optional[float] = None

    @property
    def prix_formate(self) -> Optional[str]:
        if self.prix_annuel is not None:
            return f"{self.prix_annuel:.2f} €"
        return None
    salaire_moyen: float
    poursuite_etudes: str
    taux_insertion: str
    lien_onisep: str
    resume_programme: str
    duree: str
    formation_selective: bool
    taux_passage_2e_annee: str
    acces_formation: str
    pre_bac_admission_percentage: float
    female_percentage: float
    new_bac_students_count: int
    total_admitted_count: int
    complementary_phase_acceptance_percentage: float
    taux_reussite_3_4_ans: str
    lieu: Optional[LieuSchema] = None
    salaire_bornes: Optional[SalaireBornesSchema] = None
    badges: Optional[List[BadgeSchema]] = None
    filieres_bac: Optional[List[FiliereBacSchema]] = None
    specialites_favorisees: Optional[List[SpecialiteFavoriseeSchema]] = None
    matieres_enseignees: Optional[List[MatiereEnseigneeSchema]] = None
    debouches_metiers: Optional[List[DeboucheMetierSchema]] = None
    debouches_secteurs: Optional[List[DeboucheSecteurSchema]] = None
    ts_taux_par_bac: Optional[List[TsTauxParBacSchema]] = None
    intervalles_admis: Optional[List[IntervalsAdmisSchema]] = None
    criteres_candidature: Optional[List[CriteresCandidatureSchema]] = None
    boursiers: Optional[BoursiersSchema] = None
    profils_admis: Optional[List[ProfilsAdmisSchema]] = None
    promo_characteristics: Optional[PromoCharacteristicsSchema] = None
    post_formation_outcomes: Optional[PostFormationOutcomesSchema] = None
    voie_generale: Optional[VoieSchema] = None
    voie_pro: Optional[VoieSchema] = None
    voie_technologique: Optional[VoieSchema] = None
    class Config:
        orm_mode = True

class EtablissementBase(BaseModel):
    etablissement: Optional[str] = None   # school name
    city: Optional[str] = None
    sector: Optional[str] = None          # "Privé" / "Public"
    track: Optional[str] = None           # "Général" / "Technologique" / ...

    class Config:
        orm_mode = True

class EtablissementCreate(EtablissementBase):
    academie_id: int

class EtablissementUpdate(BaseModel):
    etablissement: Optional[str] = None
    city: Optional[str] = None
    sector: Optional[str] = None
    track: Optional[str] = None
    academie_id: Optional[int] = None

    class Config:
        orm_mode = True

class EtablissementOut(EtablissementBase):
    id: int
    academie_id: int

    class Config:
        orm_mode = True


# ----- Academie -----

class AcademieBase(BaseModel):
    name: str

    class Config:
        orm_mode = True

class AcademieCreate(AcademieBase):
    pass

class AcademieUpdate(BaseModel):
    name: Optional[str] = None

    class Config:
        orm_mode = True

class AcademieOut(AcademieBase):
    id: int
    etablissements: Optional[List[EtablissementOut]] = None

    class Config:
        orm_mode = True