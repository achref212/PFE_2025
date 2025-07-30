# models/PlanAction.py
from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

class PlanAction(Base):
    __tablename__ = "plan_actions"
    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, nullable=False)
    steps = relationship("PlanStep", back_populates="plan_action", cascade="all, delete-orphan")

class PlanStep(Base):
    __tablename__ = "plan_steps"
    id = Column(Integer, primary_key=True, index=True)
    titre = Column(String, nullable=False)
    plan_action_id = Column(Integer, ForeignKey("plan_actions.id"))
    plan_action = relationship("PlanAction", back_populates="steps")
    questions = relationship("PlanQuestion", back_populates="step", cascade="all, delete-orphan")

class PlanQuestion(Base):
    __tablename__ = "plan_questions"
    id = Column(Integer, primary_key=True, index=True)
    contenu = Column(Text, nullable=False)
    step_id = Column(Integer, ForeignKey("plan_steps.id"))
    step = relationship("PlanStep", back_populates="questions")
    responses = relationship("UserPlanResponse", back_populates="question", cascade="all, delete-orphan")

class UserPlanResponse(Base):
    __tablename__ = "user_plan_response"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), index=True)
    question_id = Column(Integer, ForeignKey("plan_questions.id"), index=True)
    reponse = Column(Text)
    question = relationship("PlanQuestion", back_populates="responses")
    user = relationship("User", back_populates="plan_responses")

class UserStepAnswer(Base):
    __tablename__ = "user_step_answers"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), index=True)
    step_id = Column(Integer, ForeignKey("plan_steps.id"), index=True)
    response = Column(Text, nullable=True)
    user = relationship("User", back_populates="step_answers")
    step = relationship("PlanStep")