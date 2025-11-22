from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class ReplyBase(BaseModel):
    content: str
    reply_type: str = "official"  # official/thank
    template_id: Optional[str] = None

class ReplyCreate(ReplyBase):
    merchant_id: int
    review_id: int

class ReplyInDB(ReplyBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    merchant_id: int
    review_id: int
    created_at: datetime

class ReplyResponse(BaseModel):
    success: bool = True
    data: ReplyInDB