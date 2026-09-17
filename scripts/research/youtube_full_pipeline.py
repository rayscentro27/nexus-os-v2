#!/usr/bin/env python3
"""Bounded, local YouTube Research processing for the supervised watcher.

This module intentionally stops at local research artifacts. It does not invoke Alpha,
create opportunities, create department work orders, publish, or write Supabase records.
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common import ROOT
from research_scoring import scoring_profile

CANONICAL_ROOT = ROOT / "reports" / "runtime" / "youtube_artifacts"
YT_DLP_MAX_ATTEMPTS = 2
YT_DLP_TIMEOUT_SECONDS = 45
WHISPER_CPP_BINARY = ROOT / ".runtime" / "whisper.cpp" / "build-native" / "bin" / "whisper-cli"
WHISPER_CPP_MODEL = ROOT / ".runtime" / "whisper.cpp" / "models" / "ggml-tiny.en.bin"


def _runtime_binary(name: str) -> str:
    """Resolve host tools explicitly because launchd does not inherit shell PATH."""
    configured = os.environ.get(f"NEXUS_{name.upper().replace('-', '_')}_PATH")
    candidates = [configured, shutil.which(name), f"/usr/local/bin/{name}", f"/opt/homebrew/bin/{name}"]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    return name


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run(command: list[str], timeout: int = 180) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(command, 124, exc.stdout or "", f"command timed out after {timeout}s")


def _run_ytdlp(command: list[str]) -> subprocess.CompletedProcess[str]:
    """Retry only transient yt-dlp acquisition failures, with a hard bound."""
    command = [_runtime_binary("yt-dlp") if part == "yt-dlp" else part for part in command]
    if "--socket-timeout" not in command:
        command = [command[0], "--socket-timeout", "10", *command[1:]]
    last = subprocess.CompletedProcess(command, 1, "", "yt-dlp did not run")
    for attempt in range(1, YT_DLP_MAX_ATTEMPTS + 1):
        last = _run(command, timeout=YT_DLP_TIMEOUT_SECONDS)
        if last.returncode == 0:
            return last
        if attempt < YT_DLP_MAX_ATTEMPTS:
            time.sleep(1)
    return last


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 35]


def _caption_text(raw: str) -> tuple[str, list[dict[str, str]]]:
    segments: list[dict[str, str]] = []
    for block in re.split(r"\n\s*\n", raw):
        lines = block.splitlines()
        timing_index = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if timing_index is None:
            continue
        timestamp = lines[timing_index].split(" --> ", 1)[0].strip()
        value = " ".join(
            html.unescape(re.sub(r"<[^>]+>", "", line)).strip()
            for line in lines[timing_index + 1 :]
            if line.strip()
        )
        value = re.sub(r"\s+", " ", value).strip()
        if value and (not segments or value != segments[-1]["text"]):
            segments.append({"timestamp": timestamp, "text": value})
    return re.sub(r"\s+", " ", " ".join(s["text"] for s in segments)).strip(), segments


def _matches(text: str, terms: list[str], limit: int = 4) -> list[str]:
    found: list[str] = []
    for sentence in _sentences(text):
        if any(term in sentence.lower() for term in terms) and sentence not in found:
            found.append(sentence[:500])
    return found[:limit] or ["NOT_PRESENT"]


def _extract(text: str) -> dict[str, Any]:
    return {
        "tools": _matches(text, ["tool", "software", "claude", "gemini", "chatgpt", "tradingview"]),
        "platforms": _matches(text, ["youtube", "discord", "whatsapp", "github", "tradingview", "hyperliquid"]),
        "products_services": _matches(text, ["product", "service", "program", "course", "membership"]),
        "business_model": _matches(text, ["business model", "revenue", "funding", "service", "membership"]),
        "pricing": _matches(text, ["$", "price", "cost", "per month", "monthly", "coupon"]),
        "revenue_claims": _matches(text, ["revenue", "made $", "million", "per month", "profit"]),
        "marketing_methods": _matches(text, ["youtube", "marketing", "content", "viral", "subscribe", "audience"]),
        "lead_generation": _matches(text, ["lead", "funnel", "customer", "client", "traffic"]),
        "sales_methods": _matches(text, ["sell", "sales", "offer", "close", "checkout"]),
        "automation": _matches(text, ["automate", "automation", "routine", "agent", "prompt"]),
        "ai_technologies": _matches(text, ["ai", "gemini", "claude", "chatgpt", "mcp", "model"]),
        "credit_strategies": _matches(text, ["credit", "utilization", "score", "bureau", "trade line"]),
        "funding_strategies": _matches(text, ["funding", "loan", "business credit", "lender", "capital"]),
        "real_estate_strategies": _matches(text, ["real estate", "property", "rehab"]),
        "risks": _matches(text, ["risk", "risky", "lose", "drawdown", "caution", "guarantee"]),
        "compliance_references": _matches(text, ["compliance", "legal", "fcra", "fdcpa", "financial advice"]),
        "tactics": _matches(text, ["tactic", "strategy", "method", "step", "use"]),
        "recommendations": _matches(text, ["recommend", "should", "need to", "advice", "suggest"]),
        "follow_up_questions": [
            "What independent evidence supports the material claims?",
            "What implementation cost and compliance constraints apply?",
        ],
    }


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def _metadata(url: str, provided: dict[str, Any] | None = None) -> dict[str, Any]:
    result = _run_ytdlp(["yt-dlp", "--no-update", "--no-warnings", "--skip-download", "--dump-single-json", url])
    if result.returncode != 0:
        if provided and provided.get("title"):
            return {"id": provided.get("video_id"), "title": provided.get("title"), "channel": provided.get("channel", "UNKNOWN"), "description": provided.get("description", ""), "duration": provided.get("duration")}
        raise RuntimeError(f"metadata acquisition failed: {result.stderr[-500:].strip()}")
    return json.loads(result.stdout)


def acquire_captions(url: str, video_id: str) -> tuple[str, list[dict[str, str]], str]:
    with tempfile.TemporaryDirectory(prefix="nexus-youtube-captions-") as temp:
        result = _run_ytdlp([
            "yt-dlp", "--no-update", "--no-warnings", "--skip-download",
            "--write-subs", "--write-auto-subs", "--sub-langs", "en.*",
            "--sub-format", "vtt", "--output", str(Path(temp) / "%(id)s.%(ext)s"), url,
        ])
        caption_files = sorted(Path(temp).glob(f"{video_id}*.vtt"))
        if result.returncode != 0 or not caption_files:
            detail = (result.stderr or result.stdout)[-700:].strip()
            raise RuntimeError(f"captions unavailable: {detail or 'no English VTT returned'}")
        return (*_caption_text(caption_files[0].read_text(errors="ignore")), "public_youtube_captions")


def _acquire_audio_wav(url: str, video_id: str, temp: str) -> tuple[Path, Path]:
    temp_path = Path(temp)
    source = temp_path / f"{video_id}.source"
    audio = temp_path / f"{video_id}.wav"
    download = _run_ytdlp(["yt-dlp", "--no-update", "--no-warnings", "-f", "bestaudio/best", "-o", str(source), url])
    source_files = [p for p in temp_path.glob(f"{video_id}.source*") if p.is_file()]
    if download.returncode != 0 or not source_files:
        raise RuntimeError(f"audio acquisition failed: {(download.stderr or download.stdout)[-700:].strip()}")
    normalize = _run([_runtime_binary("ffmpeg"), "-y", "-i", str(source_files[0]), "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(audio)])
    if normalize.returncode != 0 or not audio.exists():
        raise RuntimeError(f"ffmpeg normalization failed: {normalize.stderr[-700:].strip()}")
    return audio, source_files[0]


def _acquire_audio_whisper_cpp(url: str, video_id: str) -> tuple[str, list[dict[str, str]], str, str]:
    """Use only the durable native backend when its binary and model exist."""
    if not WHISPER_CPP_BINARY.is_file() or not WHISPER_CPP_MODEL.is_file():
        raise RuntimeError("whisper.cpp unavailable: durable binary or tiny.en model is missing")
    with tempfile.TemporaryDirectory(prefix="nexus-youtube-asr-") as temp:
        audio, _source = _acquire_audio_wav(url, video_id, temp)
        output_base = Path(temp) / video_id
        result = _run([str(WHISPER_CPP_BINARY), "-m", str(WHISPER_CPP_MODEL), "-f", str(audio), "-l", "en", "-otxt", "-oj", "-of", str(output_base), "-np", "-nt"], timeout=900)
        txt_path = output_base.with_suffix(".txt")
        json_path = output_base.with_suffix(".json")
        if result.returncode != 0 or not txt_path.exists():
            raise RuntimeError(f"whisper.cpp failed (exit {result.returncode}): {(result.stderr or result.stdout)[-900:].strip()}")
        transcript = re.sub(r"\s+", " ", txt_path.read_text(errors="ignore")).strip()
        segments: list[dict[str, str]] = []
        if json_path.exists():
            try:
                payload = json.loads(json_path.read_text(errors="ignore"))
                for item in payload.get("transcription", []):
                    text = re.sub(r"\s+", " ", str(item.get("text", ""))).strip()
                    offsets = item.get("offsets", {})
                    if text:
                        segments.append({"timestamp": f"{int(offsets.get('from', 0)) / 1000:.2f}-{int(offsets.get('to', 0)) / 1000:.2f}", "text": text})
            except (ValueError, TypeError):
                segments = []
        if not transcript:
            raise RuntimeError("whisper.cpp returned an empty transcript")
        return transcript, segments, "local_whisper_cpp", "tiny.en"


def acquire_audio_asr(url: str, video_id: str) -> tuple[str, list[dict[str, str]], str, str]:
    """Acquire audio and choose the first independently available local backend."""
    if WHISPER_CPP_BINARY.is_file() and WHISPER_CPP_MODEL.is_file():
        return _acquire_audio_whisper_cpp(url, video_id)
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("ASR fallback unavailable: faster-whisper is not installed in the active worker") from exc
    model_name = os.environ.get("NEXUS_WHISPER_MODEL", "tiny.en")
    with tempfile.TemporaryDirectory(prefix="nexus-youtube-asr-") as temp:
        audio, _source = _acquire_audio_wav(url, video_id, temp)
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        parts, _info = model.transcribe(str(audio), vad_filter=True)
        segments = [{"timestamp": f"{segment.start:.2f}-{segment.end:.2f}", "text": re.sub(r"\s+", " ", segment.text).strip()} for segment in parts if segment.text.strip()]
        transcript = re.sub(r"\s+", " ", " ".join(segment["text"] for segment in segments)).strip()
        if not transcript:
            raise RuntimeError("local ASR returned an empty transcript")
        return transcript, segments, "local_faster_whisper", model_name


def _topic(metadata: dict[str, Any], transcript: str) -> str:
    blob = f"{metadata.get('title', '')} {metadata.get('description', '')} {transcript[:3000]}".lower()
    if any(x in blob for x in ["crypto", "forex", "backtest", "drawdown", "trading system"]):
        return "trading strategies"
    if any(x in blob for x in ["credit", "funding", "loan", "lender"]):
        return "business funding and credit"
    return "ai automation and online business"


def process_youtube_video(video: dict[str, Any], artifact_root: Path = CANONICAL_ROOT, force_asr: bool = False, metadata_override: dict[str, Any] | None = None) -> dict[str, Any]:
    artifact_root.mkdir(parents=True, exist_ok=True)
    url = video["url"]
    video_id = video["video_id"]
    base = artifact_root / video_id
    metadata = metadata_override or _metadata(url, video)
    title = metadata.get("title") or video.get("title") or video_id
    channel = metadata.get("channel") or metadata.get("uploader") or video.get("channel") or "UNKNOWN"
    content_hash = hashlib.sha256(json.dumps({k: metadata.get(k) for k in ("id", "title", "description", "duration", "upload_date")}, sort_keys=True, default=str).encode()).hexdigest()
    existing = base.with_suffix(".metadata.json")
    asr_backend = "NONE"
    audio_acquired = False
    ffmpeg_normalized = False
    try:
        if force_asr:
            transcript, segments, transcript_source, asr_backend = acquire_audio_asr(url, video_id)
            audio_acquired = True
            ffmpeg_normalized = True
        else:
            transcript, segments, transcript_source = acquire_captions(url, video_id)
    except Exception as caption_error:
        try:
            transcript, segments, transcript_source, asr_backend = acquire_audio_asr(url, video_id)
            audio_acquired = True
            ffmpeg_normalized = True
        except Exception as asr_error:
            failure = {"video_id": video_id, "url": url, "title": title, "channel": channel, "content_hash": content_hash, "transcript_status": "FAILED_RETRYABLE", "failure_reason": str(asr_error), "caption_failure_reason": str(caption_error), "processing_status": "FAILED_RETRYABLE", "last_processed_at": _now(), "alpha_invoked": False, "opportunities_created": 0, "work_orders_created": 0}
            _write_json(existing, failure)
            return failure
    if not transcript:
        raise RuntimeError("caption acquisition returned empty transcript")
    transcript_hash = hashlib.sha256(transcript.encode()).hexdigest()
    if existing.exists():
        prior = json.loads(existing.read_text())
        if prior.get("content_hash") == content_hash and prior.get("transcript_hash") == transcript_hash and prior.get("processing_status") == "FULLY_PROCESSED":
            return {"video_id": video_id, "title": title, "duplicate_unchanged": True, "new_artifact_set_created": False, "processing_status": "FULLY_PROCESSED", "artifact_root": str(artifact_root.relative_to(ROOT)), "content_hash": content_hash, "transcript_hash": transcript_hash}
    topic = _topic(metadata, transcript)
    sentences = _sentences(transcript)
    summary = {
        "executive_summary": f"Transcript-derived review of {title}: {(sentences[0] if sentences else transcript[:400])[:500]}",
        "main_topic": topic,
        "key_themes": [x for x, terms in (("credit/funding", ["credit", "funding"]), ("AI automation", ["ai", "agent", "automation"]), ("marketing/content", ["youtube", "marketing", "content"]), ("trading risk", ["trading", "crypto", "backtest"])) if any(t in transcript.lower() for t in terms)] or ["general business education"],
        "key_points": _matches(transcript, ["because", "how", "business", "credit", "funding", "ai", "system", "revenue"], 5),
        "important_details": _matches(transcript, ["$", "percent", "million", "month", "days", "tool", "platform"], 4),
        "actionable_ideas": _matches(transcript, ["start", "build", "use", "create", "learn", "set up", "focus"], 4),
        "risks_or_caveats": _matches(transcript, ["risk", "risky", "not financial advice", "lose", "caution", "compliance", "guarantee"], 4),
        "unanswered_questions": ["What independent evidence supports the material claims?", "What implementation cost and compliance constraints apply?"],
    }
    extraction = _extract(transcript)
    scores = scoring_profile(transcript, topic)
    score_record = {"existing_profile": scores, "category": topic, "priority": "HIGH" if scores.get("overall_score", 0) >= 75 else "MEDIUM" if scores.get("overall_score", 0) >= 50 else "LOW", "recommended_disposition": "HIGH_VALUE_REVIEW" if scores.get("overall_score", 0) >= 75 else "FOLLOW_UP_RESEARCH" if scores.get("overall_score", 0) >= 50 else "MONITOR", "alpha_invoked": False}
    transcript_path = base.with_suffix(".transcript.txt")
    transcript_path.write_text(transcript + "\n")
    provenance = [{"source_video_id": video_id, "transcript_reference": str(transcript_path.relative_to(ROOT)), "timestamp_or_segment": segment["timestamp"], "extracted_text_or_paraphrase": segment["text"][:500]} for segment in segments[:8]]
    metadata_record = {"video_id": video_id, "url": url, "channel": channel, "title": title, "source": "yt-dlp public captions" if transcript_source == "public_youtube_captions" else "yt-dlp temporary audio + local ASR", "content_hash": content_hash, "transcript_status": "ACQUIRED", "transcript_source": transcript_source, "transcript_hash": transcript_hash, "summary_status": "CREATED", "extraction_status": "CREATED", "scoring_status": "SCORED", "processing_status": "FULLY_PROCESSED", "last_processed_at": _now(), "audio_acquired": audio_acquired, "ffmpeg_normalized": ffmpeg_normalized, "asr_backend": asr_backend, "alpha_invoked": False, "opportunities_created": 0, "work_orders_created": 0}
    _write_json(existing, metadata_record)
    (base.with_suffix(".summary.md")).write_text("\n".join([f"# {title}", "", f"Executive summary: {summary['executive_summary']}", f"Main topic: {summary['main_topic']}", f"Key themes: {', '.join(summary['key_themes'])}", "", "Key points:", *[f"- {x}" for x in summary["key_points"]], "", "Risks or caveats:", *[f"- {x}" for x in summary["risks_or_caveats"]], "", "Unanswered questions:", *[f"- {x}" for x in summary["unanswered_questions"]]]) + "\n")
    _write_json(base.with_suffix(".structured-extraction.json"), extraction)
    _write_json(base.with_suffix(".provenance.json"), {"items": provenance})
    _write_json(base.with_suffix(".scores.json"), score_record)
    return {"video_id": video_id, "title": title, "channel": channel, "duplicate_unchanged": False, "new_artifact_set_created": True, "transcript_acquired": True, "transcript_word_count": len(transcript.split()), "transcript_source": transcript_source, "summary_created": True, "structured_extraction_created": True, "scored": True, "audio_acquired": audio_acquired, "ffmpeg_normalized": ffmpeg_normalized, "asr_backend": asr_backend, "processing_status": "FULLY_PROCESSED", "artifact_root": str(artifact_root.relative_to(ROOT)), "transcript_path": str(transcript_path.relative_to(ROOT)), "summary_path": str(base.with_suffix('.summary.md').relative_to(ROOT)), "structured_extraction_path": str(base.with_suffix('.structured-extraction.json').relative_to(ROOT)), "scores_path": str(base.with_suffix('.scores.json').relative_to(ROOT)), "content_hash": content_hash, "transcript_hash": transcript_hash, "alpha_invoked": False, "opportunities_created": 0, "work_orders_created": 0}


def select_channel_videos(channel_url: str, limit: int) -> list[dict[str, str]]:
    result = _run_ytdlp(["yt-dlp", "--no-update", "--no-warnings", "--flat-playlist", "--playlist-end", str(limit), "--dump-single-json", f"{channel_url.rstrip('/')}/videos"])
    if result.returncode != 0:
        raise RuntimeError(f"scheduled selection failed: {result.stderr[-500:].strip()}")
    payload = json.loads(result.stdout)
    return [{"video_id": entry.get("id"), "title": entry.get("title") or entry.get("id"), "url": entry.get("url") or f"https://www.youtube.com/watch?v={entry.get('id')}"} for entry in payload.get("entries", []) if entry.get("id")]


def run_scheduled_youtube_pipeline(resources: list[dict[str, Any]], items_per_resource: int = 1) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for resource in resources:
        try:
            selected = select_channel_videos(resource["resource_url"], max(1, min(items_per_resource, 3)))
            for item in selected:
                item["channel"] = resource.get("resource_name")
                item["source_resource_id"] = resource.get("resource_id")
                results.append(process_youtube_video(item))
        except Exception as exc:
            errors.append({"resource": resource.get("resource_name", "UNKNOWN"), "error": str(exc)})
    return {"scheduled_path_used": True, "artifact_root": str(CANONICAL_ROOT.relative_to(ROOT)), "results": results, "errors": errors, "opportunities_created": 0, "work_orders_created": 0, "alpha_invoked": False}
