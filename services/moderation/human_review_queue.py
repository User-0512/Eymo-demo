from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from services.database import Base


class HumanReviewItem(Base):
    __tablename__ = "human_review_queue"

    id = Column(Integer, primary_key=True, index=True)
    content_text = Column(Text, nullable=False)
    content_type = Column(String(50), nullable=False)  # e.g. text, image, video
    reason = Column(String(255), nullable=True)        # The reason Grok flagged it
    status = Column(String(50), default="pending_review")  # pending_review, approved, rejected
    created_at = Column(DateTime, default=datetime.utcnow)


def add_to_review_queue(db, content_text: str, content_type: str, reason: str):
    """
    Add an item to the human review queue.
    """
    item = HumanReviewItem(
        content_text=content_text,
        content_type=content_type,
        reason=reason,
        status="pending_review",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_pending_reviews(db):
    """
    Returns all items that are still awaiting human review.
    """
    return (
        db.query(HumanReviewItem)
        .filter(HumanReviewItem.status == "pending_review")
        .all()
    )


def get_pending_items(db):
    """Alias for get_pending_reviews."""
    return get_pending_reviews(db)


def update_review_status(db, item_id: int, new_status: str):
    """
    Updates the status of a review item.
    Returns the updated item, or None if not found.
    """
    item = (
        db.query(HumanReviewItem)
        .filter(HumanReviewItem.id == item_id)
        .first()
    )
    if item:
        item.status = new_status
        db.commit()
        db.refresh(item)
    return item


def approve_item(db, item_id: int):
    """Convenience wrapper to approve a review item."""
    return update_review_status(db, item_id, "approved")


def reject_item(db, item_id: int):
    """Convenience wrapper to reject a review item."""
    return update_review_status(db, item_id, "rejected")

