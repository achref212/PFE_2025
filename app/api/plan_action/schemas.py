from pydantic import BaseModel, EmailStr
from typing import Optional, List
class PlanQuestionResponse(BaseModel):
    id: int
    contenu: str
    reponse: Optional[str]

    class Config:
        orm_mode = True

class PlanStepResponse(BaseModel):
    id: int
    titre: str
    questions: List[PlanQuestionResponse]

    class Config:
        orm_mode = True

class PlanActionResponse(BaseModel):
    id: int
    nom: str
    steps: List[PlanStepResponse]

    class Config:
        orm_mode = True
class PlanAnswerUpdate(BaseModel):
    question_id: int
    reponse: str

class QuestionWithAnswer(BaseModel):
    id: int
    contenu: str
    reponse: Optional[str]

class StepWithQuestions(BaseModel):
    id: int
    titre: str
    questions: List[QuestionWithAnswer]

class PlanActionFullResponse(BaseModel):
    id: int
    nom: str
    steps: List[StepWithQuestions]


class UserPlanUpdateRequest(BaseModel):
    reponses: List[dict]  # [{"question_id": int, "reponse": str}]
# ✅ Utilisé dans les réponses (lecture seule)