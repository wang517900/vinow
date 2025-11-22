内容板块

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from uuid import UUID
from app.models.content import ContentType

class RecommendationRequest(BaseModel):
    user_id: UUID
    content_types: Optional[List[ContentType]] = None
    limit: int = Field(20, ge=1, le=100)
    exclude_viewed: bool = True
    location_bias: Optional[Dict[str, Any]] = None

class RecommendationResponse(BaseModel):
    items: List[Dict[str, Any]]
    total: int
    algorithm: str
    reasoning: Optional[str] = None

class UserProfileData(BaseModel):
    user_id: UUID
    interests: List[str] = Field(default_factory=list)
    viewed_content: List[UUID] = Field(default_factory=list)
    liked_content: List[UUID] = Field(default_factory=list)
    location_preferences: Optional[Dict[str, Any]] = None
    content_type_preferences: Dict[ContentType, float] = Field(default_factory=dict)
    last_updated: str

class SimilarContentRequest(BaseModel):
    content_id: UUID
    limit: int = Field(10, ge=1, le=50)

class TrendingContentRequest(BaseModel):
    content_type: Optional[ContentType] = None
    location: Optional[Dict[str, Any]] = None
    time_window: str = Field("24h", regex="^(1h|24h|7d|30d)$")
    limit: int = Field(20, ge=1, le=100)