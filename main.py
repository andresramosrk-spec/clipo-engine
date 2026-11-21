
import os
import tempfile
import subprocess

from pathlib import Path
from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    Body,
    Form
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from analyzer import transcribe_audio
from moments import detect_moments as find_moments

app = FastAPI(
    title="CLIPO ENGINE",
    description="AI-powered video clipping engine",
    version="1.5.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

def cleanup_files(*paths):
    for path in paths:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

@app.get("/")
def home():
    return {
        "project": "CLIPO",
        "version": "1.5.0",
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
            "1080x1920_export",
            "60_fps_export",
            "high_quality_h264",
            "streamer_camera_detection",
            "spanish_subtitles",
            "ffmpeg_video_processing",
            "video_trimming"
        ],
        "export": {
            "resolution": "1080x1920",
            "fps": 60,
            "codec": "H.264",
            "audio": "AAC",
            "format": "MP4"
        },
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
        cleanup_files(temp_path)

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

@app.post("/cut-video")
async def cut_video(
    file: UploadFile = File(...),
    start: float = Form(...),
    end: float = Form(...)
):
    allowed = {".mp4", ".mov", ".mkv", ".webm"}

    suffix = Path(file.filename or "").suffix.lower()

    input_path = None
    output_path = None

    try:
        if suffix not in allowed:
            raise HTTPException(
                status_code=400,
                detail="Formato no permitido. Usa MP4, MOV, MKV o WEBM."
            )

        if start < 0 or end <= start:
            raise HTTPException(
                status_code=400,
                detail="Los segundos de inicio y final no son válidos."
            )

        if end - start > 180:
            raise HTTPException(
                status_code=400,
                detail="La duración máxima del clip es de 180 segundos."
            )

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix
        ) as temp:
            input_path = temp.name
            total_size = 0

            while True:
                chunk = await file.read(1024 * 1024)

                if not chunk:
                    break

                total_size += len(chunk)

                if total_size > 300 * 1024 * 1024:
                    raise HTTPException(
                        status_code=413,
                        detail="El video supera el límite de 300 MB."
                    )

                temp.write(chunk)

        if total_size == 0:
            raise HTTPException(
                status_code=400,
                detail="El video está vacío."
            )

        probe = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                input_path
            ],
            capture_output=True,
            text=True,
            timeout=30
        )

        if probe.returncode != 0:
            raise HTTPException(
                status_code=400,
                detail="No se pudo leer la duración del video."
            )

        try:
            video_duration = float(probe.stdout.strip())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="No se pudo determinar la duración del video."
            )

        if end > video_duration:
            raise HTTPException(
                status_code=400,
                detail=f"El video dura {video_duration:.2f} segundos. El segundo final supera su duración."
            )

        output_fd, output_path = tempfile.mkstemp(suffix=".mp4")
        os.close(output_fd)

        video_filter = (
            "scale=1080:1920:"
            "force_original_aspect_ratio=decrease:"
            "force_divisible_by=2,"
            "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,"
            "setsar=1,"
            "fps=60"
        )

        command = [
            "ffmpeg",
            "-y",
            "-ss", str(start),
            "-i", input_path,
            "-t", str(end - start),
            "-map", "0:v:0",
            "-map", "0:a?",
            "-vf", video_filter,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "18",
            "-profile:v", "high",
            "-level", "4.2",
            "-pix_fmt", "yuv420p",
            "-r", "60",
            "-fps_mode", "cfr",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "48000",
            "-movflags", "+faststart",
            "-sn",
            "-dn",
            output_path
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=180
        )

        if result.returncode != 0 or not os.path.exists(output_path):
            raise HTTPException(
                status_code=500,
                detail="FFmpeg no pudo generar el clip."
            )

        if os.path.getsize(output_path) == 0:
            raise HTTPException(
                status_code=500,
                detail="El archivo generado está vacío."
            )

        return FileResponse(
            path=output_path,
            media_type="video/mp4",
            filename="clipo_clip_1080p_60fps.mp4",
            background=BackgroundTask(
                cleanup_files,
                input_path,
                output_path
            )
        )

    except HTTPException:
        cleanup_files(input_path, output_path)
        raise

    except subprocess.TimeoutExpired:
        cleanup_files(input_path, output_path)

        raise HTTPException(
            status_code=504,
            detail="El procesamiento tardó demasiado. Intenta con un video más corto."
        )

    except Exception as error:
        cleanup_files(input_path, output_path)

        raise HTTPException(
            status_code=500,
            detail=f"Error procesando el video: {str(error)}"
        )

    finally:
        await file.close()

@app.get("/video-engine")
def video_engine():
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            raise Exception("FFmpeg no está disponible")

        version = result.stdout.splitlines()[0]

        return {
            "status": "success",
            "engine": "FFmpeg",
            "version": version,
            "video_processing": True
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error comprobando FFmpeg: {str(error)}"
        )
