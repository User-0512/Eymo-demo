from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ContentCreate(BaseModel):
    text: str = Field(..., description="The educational content text")
    content_type: str = Field("text", description="Type of content (text, image, video)")
    difficulty: str = Field("intermediate", description="Difficulty level (beginner, intermediate, advanced)")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "text": "Photosynthesis is the process by which plants use sunlight, water, and carbon dioxide to create oxygen and energy in the form of sugar.",
                "content_type": "text",
                "difficulty": "beginner"
            }
        }
    }

class ContentUpdate(BaseModel):
    text: Optional[str] = Field(None, description="Updated text content")
    difficulty: Optional[str] = Field(None, description="Updated difficulty level")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "text": "Photosynthesis uses sunlight to convert water and CO2 into glucose and oxygen.",
                "difficulty": "intermediate"
            }
        }
    }

class ContentResponse(BaseModel):
    id: int
    author_id: int
    text: str
    subject_tag: str
    difficulty: str
    moderation_status: str
    popularity_score: float
    created_at: datetime
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "author_id": 1,
                "text": "Photosynthesis uses sunlight to convert water and CO2 into glucose and oxygen.",
                "subject_tag": "Biology",
                "difficulty": "intermediate",
                "moderation_status": "approved",
                "popularity_score": 0.0,
                "created_at": "2023-01-01T12:00:00Z"
            }
        }
    }

class PaginatedContentResponse(BaseModel):
    total: int
    page: int
    size: int
    items: List[ContentResponse]
