from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from services.database import get_db
from services.recommender.models.candidate_generation import get_candidates
from services.recommender.models.ranking_model import rank_candidates
from services.recommender.evaluation.metrics import log_clickthrough

router = APIRouter(prefix="/feed", tags=["Feed"])

@router.get("/{user_id}")
def generate_user_feed(user_id: int, limit: int = 20, db: Session = Depends(get_db)):
    """
    Generates a personalized feed of approved educational content for the user.
    """
    # 1. Candidate Generation
    candidates = get_candidates(db, user_id, limit=limit*2) # overfetch slightly for ranking
    
    if not candidates:
        return {"feed": [], "message": "No content available."}
        
    # 2. Ranking Model
    ranked_results = rank_candidates(candidates, top_n=limit)
    
    # 3. Format response (strip embeddings and sensitive data)
    feed = []
    for content, score in ranked_results:
        feed.append({
            "id": content.id,
            "author_id": content.author_id,
            "text": content.text[:100] + "..." if len(content.text) > 100 else content.text,
            "subject_tag": content.subject_tag,
            "popularity_score": content.popularity_score,
            "relevance_score": round(score, 3)
        })
        
    return {"user_id": user_id, "feed": feed}

@router.post("/{user_id}/click/{content_id}")
def register_click(user_id: int, content_id: int, subject_tag: str, db: Session = Depends(get_db)):
    """
    Endpoint for the frontend to report a user clicking/viewing a post in their feed.
    """
    interaction = log_clickthrough(db, user_id, content_id, subject_tag)
    return {"status": "success", "interaction_id": interaction.id}