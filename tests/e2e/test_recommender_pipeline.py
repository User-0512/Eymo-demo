import os
import sys

# Get project root (Eymo-demo) which is 3 levels up from this file
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.database import SessionLocal, Base, engine
from services.content_db import Content, UserInteraction
from services.recommender.features.content_embeddings import generate_embedding
from services.recommender.models.candidate_generation import get_candidates
from services.recommender.models.ranking_model import rank_candidates

def setup_test_data(db):
    print("Clearing old data and populating test database...")
    # Using raw SQL delete to clear tables
    db.query(Content).delete()
    db.query(UserInteraction).delete()
    db.commit()
    
    # Fake approved posts
    posts = [
        {"text": "Derivative power rule explained: drop the exponent and subtract one.", "tag": "Math", "pop": 85},
        {"text": "Integral calculus is the reverse of derivatives.", "tag": "Math", "pop": 70},
        {"text": "Quadratic formula song to help you memorize it for the SAT.", "tag": "Math", "pop": 90},
        {"text": "Proper deadlift form requires a flat back and driving through the heels.", "tag": "Health", "pop": 95},
        {"text": "How macronutrients work in the body: protein, carbs, fats.", "tag": "Health", "pop": 80},
        {"text": "Python tutorial: list comprehensions are faster than for-loops.", "tag": "Coding", "pop": 99},
        {"text": "React hooks explained simply for beginners.", "tag": "Coding", "pop": 88},
    ]
    
    print("Generating embeddings for test posts (this takes a few seconds)...")
    content_objects = []
    for p in posts:
        emb = generate_embedding(p["text"])
        content = Content(
            text=p["text"],
            subject_tag=p["tag"],
            popularity_score=p["pop"],
            embedding=emb
        )
        content_objects.append(content)
        
    db.add_all(content_objects)
    db.commit()
    
    # Get the inserted items to get their IDs
    all_content = db.query(Content).all()
    math_id = [c.id for c in all_content if c.subject_tag == "Math"][0]
    health_id = [c.id for c in all_content if c.subject_tag == "Health"][0]
    
    print("Logging interactions for Fake User 1 (The Math Student)...")
    db.add(UserInteraction(user_id=1, content_id=math_id, interaction_type="view", subject_tag="Math"))
    
    print("Logging interactions for Fake User 2 (The Gym Goer)...")
    db.add(UserInteraction(user_id=2, content_id=health_id, interaction_type="like", subject_tag="Health"))
    
    print("Logging interactions for Fake User 3 (New User, cold start)...")
    # User 3 gets no interactions
    db.commit()

def test_pipeline():
    db = SessionLocal()
    try:
        setup_test_data(db)
        
        users = [
            (1, "The Math Student"),
            (2, "The Gym Goer"),
            (3, "New User (Cold Start)")
        ]
        
        print("\n=== GENERATING PERSONALIZED FEEDS ===")
        for uid, desc in users:
            print(f"\n--- FEED FOR USER {uid} ({desc}) ---")
            candidates = get_candidates(db, user_id=uid, limit=10)
            ranked = rank_candidates(candidates, top_n=3)
            
            for content, score in ranked:
                print(f"[Score: {score:.3f}] [{content.subject_tag}] {content.text}")
                
    finally:
        db.close()

if __name__ == "__main__":
    test_pipeline()
