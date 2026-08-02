from sentence_transformers import SentenceTransformer

# Load the free local model once
# all-MiniLM-L6-v2 is fast, lightweight, and produces 384-dimensional embeddings
model = SentenceTransformer('all-MiniLM-L6-v2')

def generate_embedding(text: str) -> list[float]:
    """
    Generates a 384-dimensional vector embedding for the given text.
    """
    if not text:
        return [0.0] * 384
        
    embedding = model.encode(text)
    return embedding.tolist()
