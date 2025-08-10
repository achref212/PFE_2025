# app/models_academies.py
from sqlalchemy import Column, Integer, String, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.core.database import Base

class Academie(Base):
    __tablename__ = "academies"

    id = Column(Integer, primary_key=True)
    # unique name for the academie (e.g., "Versailles")
    name = Column(String, nullable=False, unique=True)
    # canonical URL to the academie listing page on letudiant.fr
    url = Column(String, nullable=False)

    # one-to-many: an academie has many etablissements
    etablissements = relationship(
        "Etablissement",
        back_populates="academie",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Academie id={self.id} name={self.name!r}>"

class Etablissement(Base):
    __tablename__ = "etablissements"

    id = Column(Integer, primary_key=True)

    # foreign key to academies
    academie_id = Column(
        Integer,
        ForeignKey("academies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # scraped fields
    etablissement = Column(String, nullable=True, index=True)  # school name
    city = Column(String, nullable=True, index=True)
    sector = Column(String, nullable=True)  # e.g., "Privé", "Public"
    track = Column(String, nullable=True)   # e.g., "Général", "Technologique", ...
    # unique identifier from site
    school_url = Column(String, nullable=False, unique=True)

    # many-to-one: link back to academie
    academie = relationship("Academie", back_populates="etablissements", lazy="joined")

    # useful composite indexes
    __table_args__ = (
        Index("ix_etablissements_acad_city", "academie_id", "city"),
        Index("ix_etablissements_acad_track", "academie_id", "track"),
    )

    def __repr__(self) -> str:
        return f"<Etablissement id={self.id} academie_id={self.academie_id} name={self.etablissement!r}>"