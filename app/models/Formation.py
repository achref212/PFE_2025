# app/models.py
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Formation(Base):
    __tablename__ = 'formations'
    id = Column(Integer, primary_key=True)
    timestamp = Column(String)
    url = Column(String, unique=True)
    titre = Column(String)
    etablissement = Column(String)
    type_formation = Column(String)
    type_etablissement = Column(String)
    formation_controlee_par_etat = Column(Boolean)
    apprentissage = Column(String)
    prix_annuel = Column(Float)
    salaire_moyen = Column(Float)
    poursuite_etudes = Column(String)
    taux_insertion = Column(String)
    lien_onisep = Column(String)
    resume_programme = Column(Text)
    duree = Column(String)
    formation_selective = Column(Boolean)
    taux_passage_2e_annee = Column(String)
    acces_formation = Column(String)
    pre_bac_admission_percentage = Column(Float)
    female_percentage = Column(Float)
    new_bac_students_count = Column(Integer)
    total_admitted_count = Column(Integer)
    complementary_phase_acceptance_percentage = Column(Float)
    taux_reussite_3_4_ans = Column(String)
    lieu = relationship("Lieu", backref="formation", uselist=False)
    salaire_bornes = relationship("SalaireBornes", backref="formation", uselist=False)
    badges = relationship("Badge", backref="formation")
    filieres_bac = relationship("FiliereBac", backref="formation")
    specialites_favorisees = relationship("SpecialiteFavorisee", backref="formation")
    matieres_enseignees = relationship("MatiereEnseignee", backref="formation")
    debouches_metiers = relationship("DeboucheMetier", backref="formation")
    debouches_secteurs = relationship("DeboucheSecteur", backref="formation")
    ts_taux_par_bac = relationship("TsTauxParBac", backref="formation")
    intervalles_admis = relationship("IntervalsAdmis", backref="formation")
    criteres_candidature = relationship("CriteresCandidature", backref="formation")
    boursiers = relationship("Boursiers", backref="formation", uselist=False)
    profils_admis = relationship("ProfilsAdmis", backref="formation")
    promo_characteristics = relationship("PromoCharacteristics", backref="formation", uselist=False)
    post_formation_outcomes = relationship("PostFormationOutcomes", backref="formation", uselist=False)
    voie_generale = relationship("VoieGenerale", backref="formation", uselist=False)
    voie_pro = relationship("VoiePro", backref="formation", uselist=False)
    voie_technologique = relationship("VoieTechnologique", backref="formation", uselist=False)
class Lieu(Base):
    __tablename__ = 'lieu'
    id = Column(Integer, primary_key=True)
    formation_id = Column(Integer, ForeignKey('formations.id', ondelete="CASCADE"))
    ville = Column(String)
    region = Column(String)
    departement = Column(String)
    academy = Column(String)
    gps_coordinates = Column(String)

class SalaireBornes(Base):
    __tablename__ = 'salaire_bornes'
    id = Column(Integer, primary_key=True)
    formation_id = Column(Integer, ForeignKey('formations.id', ondelete="CASCADE"))
    min = Column(Float)
    max = Column(Float)

class Badge(Base):
    __tablename__ = 'badges'
    id = Column(Integer, primary_key=True)
    formation_id = Column(Integer, ForeignKey('formations.id', ondelete="CASCADE"))
    badge = Column(String)

class FiliereBac(Base):
    __tablename__ = 'filieres_bac'
    id = Column(Integer, primary_key=True)
    formation_id = Column(Integer, ForeignKey('formations.id', ondelete="CASCADE"))
    filiere = Column(String)

class SpecialiteFavorisee(Base):
    __tablename__ = 'specialites_favorisees'
    id = Column(Integer, primary_key=True)
    formation_id = Column(Integer, ForeignKey('formations.id', ondelete="CASCADE"))
    specialite = Column(String)

class MatiereEnseignee(Base):
    __tablename__ = 'matieres_enseignees'
    id = Column(Integer, primary_key=True)
    formation_id = Column(Integer, ForeignKey('formations.id', ondelete="CASCADE"))
    matiere = Column(String)

class DeboucheMetier(Base):
    __tablename__ = 'debouches_metiers'
    id = Column(Integer, primary_key=True)
    formation_id = Column(Integer, ForeignKey('formations.id', ondelete="CASCADE"))
    metier = Column(String)

class DeboucheSecteur(Base):
    __tablename__ = 'debouches_secteurs'
    id = Column(Integer, primary_key=True)
    formation_id = Column(Integer, ForeignKey('formations.id', ondelete="CASCADE"))
    secteur = Column(String)

class TsTauxParBac(Base):
    __tablename__ = 'ts_taux_par_bac'
    id = Column(Integer, primary_key=True)
    formation_id = Column(Integer, ForeignKey('formations.id', ondelete="CASCADE"))
    bac_type = Column(String)
    taux = Column(String)

class IntervalsAdmis(Base):
    __tablename__ = 'intervalles_admis'
    id = Column(Integer, primary_key=True)
    formation_id = Column(Integer, ForeignKey('formations.id', ondelete="CASCADE"))
    interval_type = Column(String)
    tle_generale = Column(String)
    tle_techno = Column(String)
    tle_pro = Column(String)

class CriteresCandidature(Base):
    __tablename__ = 'criteres_candidature'
    id = Column(Integer, primary_key=True)
    formation_id = Column(Integer, ForeignKey('formations.id', ondelete="CASCADE"))
    categorie = Column(String)
    poids = Column(Float)
    sous_criteres = relationship("SousCritere", backref="criteres_candidature", cascade="all, delete-orphan")

class SousCritere(Base):
    __tablename__ = 'sous_criteres'
    id = Column(Integer, primary_key=True)
    criteres_id = Column(Integer, ForeignKey('criteres_candidature.id', ondelete="CASCADE"))
    type = Column(String)
    titre = Column(String)
    description = Column(Text)

class Boursiers(Base):
    __tablename__ = 'boursiers'
    id = Column(Integer, primary_key=True)
    formation_id = Column(Integer, ForeignKey('formations.id', ondelete="CASCADE"))
    taux_minimum_boursiers = Column(String)
    pourcentage_boursiers_neo_bacheliers = Column(Float)

class ProfilsAdmis(Base):
    __tablename__ = 'profils_admis'
    id = Column(Integer, primary_key=True)
    formation_id = Column(Integer, ForeignKey('formations.id', ondelete="CASCADE"))
    bac_type = Column(String)
    percentage = Column(Float)

class PromoCharacteristics(Base):
    __tablename__ = 'promo_characteristics'
    id = Column(Integer, primary_key=True)
    formation_id = Column(Integer, ForeignKey('formations.id', ondelete="CASCADE"))
    new_bac_students_count = Column(Integer)
    female_percentage = Column(Float)
    total_admitted_count = Column(Integer)

class PostFormationOutcomes(Base):
    __tablename__ = 'post_formation_outcomes'
    id = Column(Integer, primary_key=True)
    formation_id = Column(Integer, ForeignKey('formations.id', ondelete="CASCADE"))
    poursuivent_etudes = Column(String)
    en_emploi = Column(String)
    autre_situation = Column(String)

class VoieGenerale(Base):
    __tablename__ = 'voie_generale'
    id = Column(Integer, primary_key=True)
    formation_id = Column(Integer, ForeignKey('formations.id', ondelete="CASCADE"))
    filieres = Column(String)
    specialities = Column(String)

class VoiePro(Base):
    __tablename__ = 'voie_pro'
    id = Column(Integer, primary_key=True)
    formation_id = Column(Integer, ForeignKey('formations.id', ondelete="CASCADE"))
    filieres = Column(String)
    specialities = Column(String)

class VoieTechnologique(Base):
    __tablename__ = 'voie_technologique'
    id = Column(Integer, primary_key=True)
    formation_id = Column(Integer, ForeignKey('formations.id', ondelete="CASCADE"))
    filieres = Column(String)
    specialities = Column(String)