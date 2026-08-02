from fastapi import FastAPI
from services.api.app.routers import (
    auth,
    content,
    feed,
    moderation,
    progress,
    verification,
)

app = FastAPI(title="Eymo API")

app.include_router(auth.router)
app.include_router(content.router)
app.include_router(feed.router)
app.include_router(moderation.router)
app.include_router(progress.router)
app.include_router(verification.router)

@app.get("/")
def root():
    return {"message": "Eymo API is running"}