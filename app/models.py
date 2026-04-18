from pydantic import BaseModel

class AskRequest(BaseModel):
    question: str
    hours: int = 24