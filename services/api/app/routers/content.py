from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional, List

from services.database import get_db
from services.user_db import User
from services.content_db import Content
from services.auth_utils import get_current_user
from services.api.app.schemas.content_schemas import ContentCreate, ContentUpdate, ContentResponse, PaginatedContentResponse
from services.moderation.auto_classifier.inference import classify_content
from services.moderation.policy_rules import passes_basic_rules
from services.moderation.human_review_queue import add_to_review_queue
from services.recommender.features.content_embeddings import generate_embedding

router = APIRouter(prefix="/content", tags=["Content"])

@router.post("/", response_model=ContentResponse, status_code=status.HTTP_201_CREATED)
def create_content(
    content_in: ContentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Uploads new educational content. Automatically runs through AI moderation and embedding generation.
    """
    if content_in.content_type == "text" and not passes_basic_rules(content_in.text):
        raise HTTPException(status_code=422, detail="Failed basic quality rules (e.g. too short, spam, mostly links)")
        
    result = classify_content(content_type=content_in.content_type, text=content_in.text)
    moderation_status = result["status"]
    
    if moderation_status == "rejected":
        raise HTTPException(status_code=422, detail=f"Content rejected by AI moderator. Reason: {result.get('reason')}")
        
    embedding = generate_embedding(content_in.text) if content_in.text else None
    
    new_content = Content(
        author_id=current_user.id,
        text=content_in.text,
        subject_tag=result.get("subject_tag", "Other"),
        difficulty=result.get("difficulty", content_in.difficulty),
        moderation_status=moderation_status,
        embedding=embedding,
        popularity_score=0.0
    )
    db.add(new_content)
    db.commit()
    db.refresh(new_content)
    
    if moderation_status == "pending_review":
        add_to_review_queue(
            db, 
            content_text=content_in.text, 
            content_type=content_in.content_type, 
            reason=result.get("reason", "AI flagged for review")
        )
        
    return new_content

@router.get("/", response_model=PaginatedContentResponse)
def get_all_content(
    keyword: Optional[str] = Query(None, description="Search keyword in text"),
    category: Optional[str] = Query(None, description="Filter by subject_tag"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty"),
    moderation_status: Optional[str] = Query(None, description="Filter by moderation_status"),
    skip: int = Query(0, ge=0, description="Pagination skip"),
    limit: int = Query(20, ge=1, le=100, description="Pagination limit"),
    db: Session = Depends(get_db)
):
    """
    Retrieves all content with pagination and optional filtering.
    """
    query = db.query(Content)
    
    if keyword:
        query = query.filter(Content.text.ilike(f"%{keyword}%"))
    if category:
        query = query.filter(Content.subject_tag == category)
    if difficulty:
        query = query.filter(Content.difficulty == difficulty)
    if moderation_status:
        query = query.filter(Content.moderation_status == moderation_status)
        
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "page": (skip // limit) + 1,
        "size": len(items),
        "items": items
    }

@router.get("/{content_id}", response_model=ContentResponse)
def get_content(content_id: int, db: Session = Depends(get_db)):
    """
    Retrieves a single piece of content by ID.
    """
    content = db.query(Content).filter(Content.id == content_id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    return content

@router.put("/{content_id}", response_model=ContentResponse)
def update_content(
    content_id: int, 
    content_in: ContentUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Updates a piece of content. Only the author can update it.
    If text changes, it re-runs moderation and regenerates embeddings.
    """
    content = db.query(Content).filter(Content.id == content_id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
        
    if content.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this content")
        
    text_changed = False
    if content_in.text is not None and content_in.text != content.text:
        content.text = content_in.text
        text_changed = True
        
    if content_in.difficulty is not None:
        content.difficulty = content_in.difficulty
        
    if text_changed:
        if not passes_basic_rules(content.text):
            raise HTTPException(status_code=422, detail="Failed basic quality rules")
            
        result = classify_content(content_type="text", text=content.text)
        content.moderation_status = result["status"]
        if content.moderation_status == "rejected":
            raise HTTPException(status_code=422, detail=f"Content rejected by AI moderator. Reason: {result.get('reason')}")
            
        content.subject_tag = result.get("subject_tag", "Other")
        if "difficulty" in result:
            content.difficulty = result["difficulty"]
        content.embedding = generate_embedding(content.text)
        
        if content.moderation_status == "pending_review":
            add_to_review_queue(db, content_text=content.text, content_type="text", reason=result.get("reason", "AI flagged edit"))
            
    db.commit()
    db.refresh(content)
    return content

@router.delete("/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_content(
    content_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deletes a piece of content. Only the author can delete it.
    """
    content = db.query(Content).filter(Content.id == content_id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
        
    if content.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this content")
        
    db.delete(content)
    db.commit()
    return None