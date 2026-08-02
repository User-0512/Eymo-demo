from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    email: EmailStr = Field(..., description="Valid email address")
    password: str = Field(..., min_length=8, description="Strong password (min 8 chars)")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "username": "learning_wizard",
                "email": "wizard@example.com",
                "password": "securepassword123"
            }
        }
    }

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    created_at: datetime
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "username": "learning_wizard",
                "email": "wizard@example.com",
                "is_active": True,
                "created_at": "2023-01-01T12:00:00Z"
            }
        }
    }

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer"
            }
        }
    }

class TokenRefresh(BaseModel):
    refresh_token: str
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }
    }
