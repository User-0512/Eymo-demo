from datetime import datetime

def rank_candidates(candidates: list, top_n: int = 20) -> list:
    """
    Ranks a list of candidate tuples (Content, similarity_score) based on:
    score = (0.5 * embedding_similarity) + (0.3 * recency_score) + (0.2 * popularity_score)
    """
    ranked = []
    now = datetime.utcnow()
    
    for content, similarity_score in candidates:
        # Recency score: decays over 30 days. Max score 1.0 (just posted), min 0.0 (30+ days old)
        days_old = (now - content.created_at).days
        recency_score = max(0.0, 1.0 - (days_old / 30.0))
        
        # Popularity score: normalize assuming a max popularity of ~100 for now
        popularity_score = min(1.0, content.popularity_score / 100.0)
        
        final_score = (0.5 * similarity_score) + (0.3 * recency_score) + (0.2 * popularity_score)
        ranked.append((content, final_score))
        
    # Sort by final score descending
    ranked.sort(key=lambda x: x[1], reverse=True)
    
    # Return just the top_n Content objects (and their scores)
    return ranked[:top_n]
