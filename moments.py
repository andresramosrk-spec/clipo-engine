
import re
from collections import Counter


REACTION_WORDS = {
    "jajaja": 3,
    "jajaj": 3,
    "no puede ser": 4,
    "no puede": 2,
    "que paso": 2,
    "qué pasó": 2,
    "increible": 3,
    "increíble": 3,
    "ay no": 3,
    "dios mio": 3,
    "dios mío": 3,
    "wtf": 4,
    "bro": 1,
    "espera": 2,
    "mentira": 3,
    "nooo": 3,
    "vamos": 1,
    "cuidado": 2,
    "imposible": 3,
    "me muero": 3,
    "que": 1,
    "qué": 1
}


def normalize(text):
    return re.sub(r"\s+", " ", text.lower()).strip()


def score_segment(segment):
    text = normalize(segment.get("text", ""))
    score = 0

    for phrase, points in REACTION_WORDS.items():
        if phrase in text:
            score += points

    if "!" in text or "?" in text:
        score += 1

    if len(text) > 45:
        score += 1

    if len(text) < 8:
        score -= 1

    return max(0, score)


def detect_moments(transcription, max_clips=5):
    segments = transcription.get("segments", [])

    if not segments:
        return []

    candidates = []

    for i, segment in enumerate(segments):
        start = float(segment.get("start", 0))
        end = float(segment.get("end", start))

        if end <= start:
            continue

        # Añadir contexto antes y después del momento
        clip_start = max(0, start - 8)
        clip_end = end + 12

        context = [
            item for item in segments
            if float(item.get("end", 0)) >= clip_start
            and float(item.get("start", 0)) <= clip_end
        ]

        combined_text = " ".join(
            item.get("text", "") for item in context
        )

        score = sum(score_segment(item) for item in context)

        duration = clip_end - clip_start

        if duration < 15:
            score += 1

        if duration > 90:
            score -= 3

        candidates.append({
            "start": round(clip_start, 2),
            "end": round(clip_end, 2),
            "score": score,
            "transcript": combined_text.strip()
        })

    candidates.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    selected = []

    for candidate in candidates:
        overlaps = any(
            candidate["start"] < item["end"]
            and candidate["end"] > item["start"]
            for item in selected
        )

        if not overlaps:
            selected.append(candidate)

        if len(selected) >= max_clips:
            break

    selected.sort(key=lambda item: item["start"])

    for index, item in enumerate(selected, start=1):
        item["clip_number"] = index

    return selected[:max_clips]
