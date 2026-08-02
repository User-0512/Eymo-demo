from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from services.database import get_db
from services.moderation.human_review_queue import (
    get_pending_reviews,
    update_review_status,
)
from services.moderation.fact_check.fact_check_service import verify_facts

router = APIRouter(prefix="/moderation", tags=["Moderation"])


class ReviewUpdate(BaseModel):
    status: str  # "approved" or "rejected"


class FactCheckRequest(BaseModel):
    text: str


@router.get("/check")
def moderation_check():
    """Health-check endpoint for the moderation service."""
    return {"status": "Moderation service is running"}


@router.get("/pending")
def list_pending_reviews(db: Session = Depends(get_db)):
    """Lists all items awaiting human review."""
    items = get_pending_reviews(db)
    return {"pending_items": items}


@router.post("/review/{item_id}")
def review_item(item_id: int, review: ReviewUpdate, db: Session = Depends(get_db)):
    """Approves or rejects a human-review-queue item."""
    if review.status not in ["approved", "rejected"]:
        raise HTTPException(status_code=400, detail="Status must be approved or rejected")

    updated_item = update_review_status(db, item_id, review.status)
    if not updated_item:
        raise HTTPException(status_code=404, detail="Item not found")

    return {"status": "success", "item": updated_item}


@router.post("/fact-check")
def fact_check(request: FactCheckRequest):
    """Runs a fact-check on the provided text."""
    result = verify_facts(request.text)
    return result

