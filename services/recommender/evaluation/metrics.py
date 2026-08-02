def precision_at_k(recommended_ids: list, relevant_ids: list, k: int) -> float:
    """
    Calculates Precision@K: the proportion of recommended items in the top K set that are relevant.
    """
    top_k_recommended = recommended_ids[:k]
    relevant_and_recommended = [item for item in top_k_recommended if item in relevant_ids]
    return len(relevant_and_recommended) / k if k > 0 else 0.0

def recall_at_k(recommended_ids: list, relevant_ids: list, k: int) -> float:
    """
    Calculates Recall@K: the proportion of relevant items that are found in the top K recommendations.
    """
    top_k_recommended = recommended_ids[:k]
    relevant_and_recommended = [item for item in top_k_recommended if item in relevant_ids]
    return len(relevant_and_recommended) / len(relevant_ids) if relevant_ids else 0.0

def log_clickthrough(db, user_id: int, content_id: int, subject_tag: str):
    """
    Logs when a user clicks a recommended post.
    This simulates the feedback loop for the recommender engine.
    """
    from services.content_db import UserInteraction
    
    interaction = UserInteraction(
        user_id=user_id,
        content_id=content_id,
        interaction_type="view",
        subject_tag=subject_tag
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    return interaction
