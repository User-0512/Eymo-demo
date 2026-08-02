from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from services.content_db import Content, UserInteraction
import numpy as np

def get_candidates(db: Session, user_id: int, limit: int = 50):
    """
    Candidate generation for the recommender.
    If the user has history, uses pgvector cosine similarity based on their top tags.
    If no history, returns most popular recent posts.
    """
    # 1. Check if user has history
    recent_interactions = db.query(UserInteraction)\
        .filter(UserInteraction.user_id == user_id)\
        .filter(UserInteraction.timestamp >= datetime.utcnow() - timedelta(days=30))\
        .all()
        
    if not recent_interactions:
        # Cold start: most-viewed/liked approved posts from the last 7 days
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        candidates = db.query(Content)\
            .filter(Content.created_at >= seven_days_ago)\
            .order_by(Content.popularity_score.desc())\
            .limit(limit)\
            .all()
        return [(c, 0.0) for c in candidates] # (Content, similarity_score)
        
    # 2. User has history. Find their top 2-3 most-engaged tags.
    tag_counts = {}
    for interaction in recent_interactions:
        if interaction.subject_tag:
            tag_counts[interaction.subject_tag] = tag_counts.get(interaction.subject_tag, 0) + 1
            
    # Sort tags by count
    top_tags = sorted(tag_counts, key=tag_counts.get, reverse=True)[:3]
    
    # Check if we are running in a SQLite fallback mode for sandbox testing
    engine_name = db.bind.dialect.name
    
    if engine_name == "sqlite":
        # SQLite Sandbox Fallback: Since sqlite doesn't have pgvector <=> operator,
        # we will fetch the content in the top tags and calculate cosine similarity in python
        # for testing purposes only.
        
        # Get a representative embedding for the user (average of interacted content embeddings)
        # In a real system, you'd maintain a user profile vector.
        interacted_content_ids = [i.content_id for i in recent_interactions]
        interacted_contents = db.query(Content).filter(Content.id.in_(interacted_content_ids)).all()
        valid_embeddings = [c.embedding for c in interacted_contents if c.embedding is not None]
        
        if valid_embeddings:
            user_profile = np.mean(valid_embeddings, axis=0)
        else:
            user_profile = np.zeros(384)
            
        candidate_pool = db.query(Content).filter(Content.subject_tag.in_(top_tags)).all()
        
        results = []
        for c in candidate_pool:
            if c.embedding is not None:
                # Cosine similarity in numpy
                sim = np.dot(user_profile, c.embedding) / (np.linalg.norm(user_profile) * np.linalg.norm(c.embedding) + 1e-9)
            else:
                sim = 0.0
            results.append((c, float(sim)))
            
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]
        
    else:
        # PRODUCTION: Native Postgres pgvector cosine similarity
        
        # We approximate a user's interest vector by finding the most recent content they interacted with,
        # or by taking a mean vector. For simplicity here, we'll take their last interacted item's embedding.
        last_interaction = sorted(recent_interactions, key=lambda x: x.timestamp, reverse=True)[0]
        last_content = db.query(Content).filter(Content.id == last_interaction.content_id).first()
        
        if not last_content or not last_content.embedding:
            # Fallback if no embedding available
            candidates = db.query(Content).filter(Content.subject_tag.in_(top_tags)).order_by(Content.popularity_score.desc()).limit(limit).all()
            return [(c, 0.0) for c in candidates]

        # Use pgvector `<=>` operator for cosine distance (1 - cosine_similarity)
        # We order by distance ascending, which is similarity descending
        candidates = db.query(Content)\
            .filter(Content.subject_tag.in_(top_tags))\
            .order_by(Content.embedding.cosine_distance(last_content.embedding))\
            .limit(limit)\
            .all()
            
        # To strictly match the API, we need to return (content, similarity)
        # We could query the distance explicitly, but for now we'll just assign a generic high sim score
        # since the ranking_model expects it.
        # Alternatively, we can query it explicitly:
        results = db.query(
            Content, 
            (1 - Content.embedding.cosine_distance(last_content.embedding)).label('similarity')
        )\
        .filter(Content.subject_tag.in_(top_tags))\
        .order_by(Content.embedding.cosine_distance(last_content.embedding))\
        .limit(limit)\
        .all()
        
        return results
