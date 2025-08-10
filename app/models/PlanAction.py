# models/plan.py
from sqlalchemy import (
    Column, Integer, String, ForeignKey, Text, Date, Boolean, DateTime, func,
    UniqueConstraint, CheckConstraint, Index, text
)
from sqlalchemy.orm import relationship
from app.core.database import Base

class PlanAction(Base):
    __tablename__ = "plan_actions"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, nullable=False)
    start_date = Column(Date, nullable=True)
    end_date   = Column(Date, nullable=True)
    is_active  = Column(Boolean, nullable=False, server_default=text("true"))

    __table_args__ = (
        CheckConstraint(
            "(start_date IS NULL OR end_date IS NULL) OR (start_date <= end_date)",
            name="ck_plan_period_valid"
        ),
        Index("ix_plan_actions_period", "start_date", "end_date"),
    )

    steps = relationship(
        "PlanStep",
        back_populates="plan_action",
        order_by="PlanStep.ordre",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    users = relationship("User", back_populates="plan_action")

class PlanStep(Base):
    __tablename__ = "plan_steps"

    id = Column(Integer, primary_key=True, index=True)
    plan_action_id = Column(
        Integer, ForeignKey("plan_actions.id", ondelete="CASCADE"),
        index=True, nullable=False
    )
    titre = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    ordre = Column(Integer, nullable=False)   # 1..6
    start_date = Column(Date, nullable=True)
    end_date   = Column(Date, nullable=True)

    __table_args__ = (
        UniqueConstraint("plan_action_id", "ordre", name="uq_planstep_plan_ordre"),
        CheckConstraint("ordre >= 1", name="ck_planstep_ordre_positive"),
        CheckConstraint(
            "(start_date IS NULL OR end_date IS NULL) OR (start_date <= end_date)",
            name="ck_planstep_period_valid"
        ),
        Index("ix_plan_steps_period", "start_date", "end_date"),
    )

    plan_action = relationship("PlanAction", back_populates="steps")
    user_progress = relationship(
        "UserStepProgress",
        back_populates="step",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

class UserStepProgress(Base):
    __tablename__ = "user_step_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("user.id", ondelete="CASCADE"),
        index=True, nullable=False
    )
    step_id = Column(
        Integer, ForeignKey("plan_steps.id", ondelete="CASCADE"),
        index=True, nullable=False
    )
    is_done = Column(Boolean, nullable=False, server_default=text("false"))
    done_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "step_id", name="uq_user_step_once"),
        Index("ix_user_step_progress_user_step", "user_id", "step_id"),
    )

    user = relationship("User", back_populates="step_progress")
    step = relationship("PlanStep", back_populates="user_progress")