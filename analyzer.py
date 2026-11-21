
import os
from faster_whisper import WhisperModel

MODEL_SIZE = os.getenv("WHISPER_MODEL", "base")
_model = None

def get_model():
    global _model

    if _model is None:
        _model = WhisperModel(
            MODEL_SIZE,
            device="cpu",
            compute_type="int8"
        )

    return _model


def transcribe_audio(audio_path):
    model = get_model()

    segments, info = model.transcribe(
        audio_path,
        beam_size=3,
        vad_filter=True,
        word_timestamps=True
    )

    results = []

    for segment in segments:
        words = []

        if segment.words:
            for word in segment.words:
                words.append({
                    "text": word.word.strip(),
                    "start": round(word.start, 3),
                    "end": round(word.end, 3)
                })

        results.append({
            "text": segment.text.strip(),
            "start": round(segment.start, 3),
            "end": round(segment.end, 3),
            "words": words
        })

    return {
        "language": info.language,
        "language_probability": info.language_probability,
        "segments": results
    }
