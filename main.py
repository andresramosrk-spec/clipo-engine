
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone

app = FastAPI(
    title="CLIPO ENGINE",
    description="AI-powered video clipping engine",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {
        "project": "CLIPO",
        "message": "Welcome to Clipo Engine",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "engine": "CLIPO",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/capabilities")
def capabilities():
    return {
        "platforms": ["youtube", "kick", "upload"],
        "features": [
            "smart_moment_detection",
            "automatic_clipping",
            "manual_clip_selection",
            "vertical_9_16",
            "streamer_camera_detection",
            "automatic_subtitles"
        ],
        "status": "development"
    }
