
import os
import tempfile

from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware

from analyzer import transcribe_audio
from moments import detect_moments as find_moments

app = FastAPI(
    title="CLIPO ENGINE",
    description="AI-powered video clipping engine",
    version="1.2.0"
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
        "version": "1.2.0",
        "status": "running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "engine": "CLIPO"
    }


@app.get("/capabilities")
def capabilities():
    return {
        "platforms": ["youtube", "kick", "upload"],
        "features": [
            "audio_transcription",
            "word_timestamps",
            "smart_moment_detection",
            "top_5_clips",
            "automatic_clipping",
            "manual_clip_selection",
            "vertical_9_16",
            "streamer_camera_detection",
            "spanish_subtitles"
        ],
        "status": "development"
    }


@app.post("/analyze-audio")
async def analyze_audio(file: UploadFile = File(...)):
    allowed = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}

    suffix = Path(file.filename or "").suffix.lower()

    if suffix not in allowed:
        raise HTTPException(
            status_code=400,
            detail="Formato no permitido. Usa MP3, WAV, M4A, AAC, OGG o FLAC."
        )

    temp_path = None

    try:
        content = await file.read()

        if not content:
            raise HTTPException(
                status_code=400,
                detail="El archivo está vacío."
            )

        if len(content) > 100 * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail="Máximo 100 MB."
            )

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix
        ) as temp:
            temp.write(content)
            temp_path = temp.name

        result = transcribe_audio(temp_path)

        return {
            "status": "success",
            "message": "Audio analizado correctamente",
            "result": result
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error al analizar el audio: {str(error)}"
        )

    finally:
        await file.close()

        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


@app.post("/detect-moments")
def detect_moments_endpoint(payload: dict = Body(...)):
    try:
        transcription = payload.get("transcription", payload)

        if not isinstance(transcription, dict):
            raise HTTPException(
                status_code=400,
                detail="La transcripción debe ser un objeto."
            )

        if not isinstance(transcription.get("segments"), list):
            raise HTTPException(
                status_code=400,
                detail="Falta la lista de segmentos de la transcripción."
            )

        moments = find_moments(
            transcription,
            max_clips=5
        )

        return {
            "status": "success",
            "message": "Detección de momentos completada",
            "clips_found": len(moments),
            "max_clips": 5,
            "moments": moments
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error detectando momentos: {str(error)}"
        )
