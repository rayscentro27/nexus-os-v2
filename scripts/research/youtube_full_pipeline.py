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
import signal
import subprocess
import ssl
import tempfile
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common import ROOT
from research_scoring import scoring_profile
from asr_worker_router import dispatch_oracle

CANONICAL_ROOT = ROOT / "reports" / "runtime" / "youtube_artifacts"
YT_DLP_MAX_ATTEMPTS = 1
# Each provider attempt is bounded.  The worker remains one-video-at-a-time;
# this is deliberately not a mass ASR fanout on the Mac mini.
YT_DLP_TIMEOUT_SECONDS = 35
YOUTUBE_ASR_TIMEOUT_SECONDS = 120
YOUTUBE_ASR_CHUNK_SECONDS = 240
# A 535-second captionless sample exhausted three 90-second chunk budgets
# while the worker was still in the bounded ASR ladder.  Keep the fallback
# bounded, but give each chunk enough CPU time and the whole sample enough
# budget to complete ordinary short/medium videos.
YOUTUBE_ASR_CHUNK_TIMEOUT_SECONDS = 180
YOUTUBE_ASR_TOTAL_TIMEOUT_SECONDS = 900
YOUTUBE_ASR_THREADS = 8
WHISPER_CPP_BINARY = ROOT / ".runtime" / "whisper.cpp" / "build-native" / "bin" / "whisper-cli"
WHISPER_CPP_MODEL = ROOT / ".runtime" / "whisper.cpp" / "models" / "ggml-tiny.en.bin"
FASTER_WHISPER_PYTHON = Path(os.environ.get("NEXUS_FASTER_WHISPER_PYTHON", str(ROOT / ".runtime" / "faster-whisper-venv" / "bin" / "python")))
FASTER_WHISPER_HELPER = Path(__file__).with_name("faster_whisper_worker.py")


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
    process: subprocess.Popen[str] | None = None
    try:
        process = subprocess.Popen(command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        stdout, stderr = process.communicate(timeout=timeout)
        return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
    except subprocess.TimeoutExpired as exc:
        if process is not None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
                stdout, stderr = process.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                stdout, stderr = process.communicate()
            except ProcessLookupError:
                stdout, stderr = "", ""
        else:
            stdout, stderr = exc.stdout or "", exc.stderr or ""
        return subprocess.CompletedProcess(command, 124, stdout or "", f"command timed out after {timeout}s")


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


def _http_get(url: str, timeout: int = 15) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 Nexus Research/2.0"})
    context = None
    try:
        import certifi
        context = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        context = None
    with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
        return response.read()


def _rss_channel_videos(channel_url: str, limit: int) -> list[dict[str, str]]:
    """Bounded metadata-only fallback when the yt-dlp Python runtime hangs."""
    parsed = urllib.parse.urlparse(channel_url)
    channel_id = ""
    if "/channel/" in parsed.path:
        channel_id = parsed.path.split("/channel/", 1)[1].split("/", 1)[0]
    if not channel_id:
        raise RuntimeError("RSS fallback requires a canonical YouTube channel id")
    root = ET.fromstring(_http_get(f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"))
    ns = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
    videos = []
    for entry in root.findall("atom:entry", ns)[:max(1, min(limit, 10))]:
        video_id = entry.findtext("yt:videoId", default="", namespaces=ns)
        title = entry.findtext("atom:title", default=video_id, namespaces=ns)
        published = entry.findtext("atom:published", default="", namespaces=ns)
        if video_id:
            videos.append({"video_id": video_id, "title": title, "url": f"https://www.youtube.com/watch?v={video_id}",
                           "published_at": published, "discovery_method": "YOUTUBE_RSS"})
    return videos


def _http_caption_tracks(url: str, video_id: str) -> tuple[str, list[dict[str, str]], str]:
    """Read public caption tracks from the video page without downloading media."""
    page = _http_get(url)
    text = page.decode("utf-8", errors="ignore")
    player_match = re.search(r"var ytInitialPlayerResponse\s*=\s*(\{.*?\});", text)
    if player_match:
        player = json.loads(player_match.group(1))
        tracks = player.get("captions", {}).get("playerCaptionsTracklistRenderer", {}).get("captionTracks", [])
    else:
        marker = '"captionTracks":'
        start = text.find(marker)
        start = text.find("[", start + len(marker)) if start >= 0 else -1
        if start < 0:
            raise RuntimeError("no public caption tracks exposed in video page")
        depth = 0
        end = None
        for index in range(start, len(text)):
            if text[index] == "[": depth += 1
            elif text[index] == "]":
                depth -= 1
                if depth == 0:
                    end = index + 1
                    break
        if end is None:
            raise RuntimeError("caption track payload is incomplete")
        tracks = json.loads(text[start:end])
    track = next((x for x in tracks if str(x.get("languageCode", "")).startswith("en")), tracks[0] if tracks else None)
    if not track or not track.get("baseUrl"):
        raise RuntimeError("no English public caption track")
    caption_xml = _http_get(track["baseUrl"])
    if not caption_xml.strip():
        raise RuntimeError("public caption endpoint returned an empty response")
    root = ET.fromstring(caption_xml)
    segments = []
    for node in root.findall("text"):
        value = html.unescape(re.sub(r"<[^>]+>", "", node.text or ""))
        value = re.sub(r"\s+", " ", value).strip()
        if value:
            seconds = float(node.get("start", "0"))
            segments.append({"timestamp": f"{seconds:.2f}", "text": value})
    transcript = re.sub(r"\s+", " ", " ".join(x["text"] for x in segments)).strip()
    if not transcript:
        raise RuntimeError(f"empty public caption track for {video_id}")
    return transcript, segments, "public_youtube_captions_http"


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


def _artifact_ref(path: Path) -> str:
    """Return a stable repo-relative path, or an absolute isolated-test path."""
    resolved = Path(path).resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def _metadata(url: str, provided: dict[str, Any] | None = None) -> dict[str, Any]:
    if provided and provided.get("discovery_method") == "YOUTUBE_RSS":
        return {"id": provided.get("video_id"), "title": provided.get("title"),
                "channel": provided.get("channel", "UNKNOWN"), "description": provided.get("description", ""),
                "duration": provided.get("duration"), "upload_date": provided.get("published_at", "")}
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
            return _http_caption_tracks(url, video_id)
        return (*_caption_text(caption_files[0].read_text(errors="ignore")), "public_youtube_captions")


def _acquire_audio_wav(url: str, video_id: str, temp: str) -> tuple[Path, Path]:
    temp_path = Path(temp)
    source = temp_path / f"{video_id}.source"
    audio = temp_path / f"{video_id}.wav"
    # The default YouTube web client can expose metadata/captions while
    # rejecting the media URL with HTTP 403.  Android client format URLs are
    # available for the same public video and keep this fallback within the
    # existing yt-dlp path; do not introduce a second downloader.
    download = _run_ytdlp([
        "yt-dlp", "--no-update", "--no-warnings",
        "--extractor-args", "youtube:player_client=android",
        "-f", "bestaudio/best", "-o", str(source), url,
    ])
    source_files = [p for p in temp_path.glob(f"{video_id}.source*") if p.is_file()]
    if download.returncode != 0 or not source_files:
        raise RuntimeError(f"audio acquisition failed: {(download.stderr or download.stdout)[-700:].strip()}")
    normalize = _run([_runtime_binary("ffmpeg"), "-y", "-i", str(source_files[0]), "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(audio)])
    if normalize.returncode != 0 or not audio.exists():
        raise RuntimeError(f"ffmpeg normalization failed: {normalize.stderr[-700:].strip()}")
    return audio, source_files[0]


def _split_audio_chunks(audio: Path, temp: Path, chunk_seconds: int) -> list[Path]:
    chunk_dir = temp / "chunks"
    chunk_dir.mkdir(parents=True, exist_ok=True)
    result = _run([
        _runtime_binary("ffmpeg"), "-y", "-i", str(audio), "-f", "segment",
        "-segment_time", str(chunk_seconds), "-reset_timestamps", "1",
        "-c", "copy", str(chunk_dir / "chunk_%03d.wav"),
    ], timeout=30)
    chunks = sorted(chunk_dir.glob("chunk_*.wav"))
    if result.returncode != 0 or not chunks:
        raise RuntimeError(f"audio chunking failed (exit {result.returncode}): {result.stderr[-900:].strip()}")
    return chunks


def _acquire_audio_faster_whisper(url: str, video_id: str) -> tuple[str, list[dict[str, str]], str, str, dict[str, Any]]:
    """Run the faster-whisper backend in its compatible Python environment."""
    if not FASTER_WHISPER_PYTHON.is_file() or not FASTER_WHISPER_HELPER.is_file():
        raise RuntimeError("faster-whisper unavailable: compatible Python environment or helper is missing")
    with tempfile.TemporaryDirectory(prefix="nexus-youtube-faster-whisper-") as temp:
        audio, _source = _acquire_audio_wav(url, video_id, temp)
        oracle_error = None
        if os.environ.get("NEXUS_DISABLE_ORACLE_ASR", "0") != "1":
            try:
                transcript, diagnostics = dispatch_oracle(audio, job_id=f"youtube-{video_id}-{int(time.time())}", video_id=video_id)
                return transcript, [], "oracle_faster_whisper", "oracle_faster_whisper", diagnostics
            except Exception as exc:  # Oracle is a worker preference; Mac remains the certified fallback.
                oracle_error = str(exc)
        transcript_path = Path(temp) / "transcript.txt"
        progress_path = Path(temp) / "progress.json"
        result_path = Path(temp) / "result.json"
        started_at = _now()
        started = time.monotonic()
        model_name = os.environ.get("NEXUS_WHISPER_MODEL", "tiny.en")
        process = subprocess.Popen(
            [str(FASTER_WHISPER_PYTHON), str(FASTER_WHISPER_HELPER), str(audio), str(transcript_path), str(progress_path), str(result_path), model_name],
            cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
        )
        last_progress: dict[str, Any] = {"words_written": 0, "current_chunk": 1, "total_chunks": 1}
        while process.poll() is None:
            if progress_path.exists():
                try:
                    last_progress = json.loads(progress_path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    pass
            if time.monotonic() - started >= YOUTUBE_ASR_TOTAL_TIMEOUT_SECONDS:
                os.killpg(process.pid, signal.SIGTERM)
                stdout, stderr = process.communicate(timeout=5)
                raise RuntimeError(json.dumps({"error": "faster-whisper timeout", "asr_started_at": started_at,
                                               "last_progress": last_progress, "stderr": stderr[-500:]}))
            time.sleep(1)
        stdout, stderr = process.communicate()
        if process.returncode != 0 or not result_path.exists() or not transcript_path.exists():
            raise RuntimeError(json.dumps({"error": "faster-whisper failed", "returncode": process.returncode,
                                           "last_progress": last_progress, "stderr": stderr[-700:], "stdout": stdout[-300:]}))
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        transcript = re.sub(r"\s+", " ", str(payload.get("transcript", ""))).strip()
        if not transcript:
            raise RuntimeError("faster-whisper returned an empty transcript")
        diagnostics = {
            "status": "FULL_TRANSCRIPT", "audio_duration_seconds": payload.get("audio_duration_seconds"),
            "asr_started_at": started_at, "model": model_name, "current_chunk": 1, "total_chunks": 1,
            "words_written": len(transcript.split()), "last_progress_at": last_progress.get("last_progress_at", _now()),
            "runtime_seconds": round(time.monotonic() - started, 3), "engine": "faster-whisper",
            "cpu_threads": 4, "compute_type": "int8",
            "cpu_percent_estimate": payload.get("cpu_percent_estimate"),
            "cpu_user_seconds": payload.get("cpu_user_seconds"),
            "cpu_system_seconds": payload.get("cpu_system_seconds"),
            "ram_peak_bytes": payload.get("ram_peak_bytes"),
            "stderr": stderr[-300:],
            "routing": {"primary_worker": "oracle", "fallback_worker": "mac", "final_worker": "mac",
                         "reason": "Oracle unavailable or retryable technical failure", "oracle_error": oracle_error},
        }
        return transcript, payload.get("segments", []), "local_faster_whisper", "local_faster_whisper", diagnostics


def _acquire_audio_whisper_cpp(url: str, video_id: str) -> tuple[str, list[dict[str, str]], str, str, dict[str, Any]]:
    """Use only the durable native backend when its binary and model exist."""
    if not WHISPER_CPP_BINARY.is_file() or not WHISPER_CPP_MODEL.is_file():
        raise RuntimeError("whisper.cpp unavailable: durable binary or tiny.en model is missing")
    with tempfile.TemporaryDirectory(prefix="nexus-youtube-asr-") as temp:
        audio, _source = _acquire_audio_wav(url, video_id, temp)
        chunks = _split_audio_chunks(audio, Path(temp), YOUTUBE_ASR_CHUNK_SECONDS)
        started = time.monotonic()
        successful: list[tuple[int, str, list[dict[str, str]]]] = []
        failed: list[dict[str, Any]] = []
        for index, chunk in enumerate(chunks):
            elapsed = time.monotonic() - started
            if elapsed >= YOUTUBE_ASR_TOTAL_TIMEOUT_SECONDS:
                failed.append({"index": index, "start_seconds": index * YOUTUBE_ASR_CHUNK_SECONDS,
                               "end_seconds": (index + 1) * YOUTUBE_ASR_CHUNK_SECONDS,
                               "error": "total ASR budget exhausted"})
                continue
            output_base = Path(temp) / f"chunk_{index:03d}"
            result = _run([str(WHISPER_CPP_BINARY), "-m", str(WHISPER_CPP_MODEL), "-t", str(YOUTUBE_ASR_THREADS), "-f", str(chunk), "-l", "en", "-otxt", "-oj", "-of", str(output_base), "-np", "-nt"], timeout=min(YOUTUBE_ASR_CHUNK_TIMEOUT_SECONDS, max(1, int(YOUTUBE_ASR_TOTAL_TIMEOUT_SECONDS - elapsed))))
            txt_path = output_base.with_suffix(".txt")
            json_path = output_base.with_suffix(".json")
            if result.returncode != 0 or not txt_path.exists():
                failed.append({"index": index, "start_seconds": index * YOUTUBE_ASR_CHUNK_SECONDS,
                               "end_seconds": (index + 1) * YOUTUBE_ASR_CHUNK_SECONDS,
                               "error": (result.stderr or result.stdout or f"exit {result.returncode}")[-900:]})
                continue
            text = re.sub(r"\s+", " ", txt_path.read_text(errors="ignore")).strip()
            if not text:
                failed.append({"index": index, "start_seconds": index * YOUTUBE_ASR_CHUNK_SECONDS,
                               "end_seconds": (index + 1) * YOUTUBE_ASR_CHUNK_SECONDS,
                               "error": "whisper.cpp returned an empty transcript"})
                continue
            chunk_segments: list[dict[str, str]] = []
            if json_path.exists():
                try:
                    payload = json.loads(json_path.read_text(errors="ignore"))
                    for item in payload.get("transcription", []):
                        segment_text = re.sub(r"\s+", " ", str(item.get("text", ""))).strip()
                        offsets = item.get("offsets", {})
                        if segment_text:
                            start = index * YOUTUBE_ASR_CHUNK_SECONDS + int(offsets.get("from", 0)) / 1000
                            end = index * YOUTUBE_ASR_CHUNK_SECONDS + int(offsets.get("to", 0)) / 1000
                            chunk_segments.append({"timestamp": f"{start:.2f}-{end:.2f}", "text": segment_text})
                except (ValueError, TypeError):
                    chunk_segments = []
            successful.append((index, text, chunk_segments or [{"timestamp": f"{index * YOUTUBE_ASR_CHUNK_SECONDS:.2f}", "text": text}]))
        if not successful:
            raise RuntimeError(json.dumps({"error": "all ASR chunks failed", "failed_chunks": failed}))
        successful.sort(key=lambda row: row[0])
        transcript = re.sub(r"\s+", " ", " ".join(row[1] for row in successful)).strip()
        segments = [segment for row in successful for segment in row[2]]
        diagnostics = {"status": "FULL_TRANSCRIPT" if not failed else "PARTIAL_TRANSCRIPT",
                       "chunk_duration_seconds": YOUTUBE_ASR_CHUNK_SECONDS,
                       "chunk_timeout_seconds": YOUTUBE_ASR_CHUNK_TIMEOUT_SECONDS,
                       "total_timeout_seconds": YOUTUBE_ASR_TOTAL_TIMEOUT_SECONDS,
                       "threads": YOUTUBE_ASR_THREADS,
                       "chunk_count": len(chunks), "completed_chunks": len(successful),
                       "failed_chunks": failed}
        return transcript, segments, "local_whisper_cpp_chunked", "local_whisper_cpp_chunked", diagnostics


def acquire_audio_asr(url: str, video_id: str) -> tuple[str, list[dict[str, str]], str, str, dict[str, Any]]:
    """Acquire audio and choose the first independently available local backend."""
    faster_error = None
    try:
        return _acquire_audio_faster_whisper(url, video_id)
    except Exception as exc:
        faster_error = str(exc)
    if WHISPER_CPP_BINARY.is_file() and WHISPER_CPP_MODEL.is_file():
        try:
            return _acquire_audio_whisper_cpp(url, video_id)
        except Exception as exc:
            raise RuntimeError(json.dumps({"primary_faster_whisper": faster_error, "secondary_whisper_cpp": str(exc)})) from exc
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
        return transcript, segments, "local_faster_whisper", model_name, {"status": "FULL_TRANSCRIPT", "chunk_count": 1, "completed_chunks": 1, "failed_chunks": []}


def _topic(metadata: dict[str, Any], transcript: str) -> str:
    blob = f"{metadata.get('title', '')} {metadata.get('description', '')} {transcript[:3000]}".lower()
    if any(x in blob for x in ["crypto", "forex", "backtest", "drawdown", "trading system"]):
        return "trading strategies"
    if any(x in blob for x in ["credit", "funding", "loan", "lender"]):
        return "business funding and credit"
    return "ai automation and online business"


def process_youtube_video(video: dict[str, Any], artifact_root: Path = CANONICAL_ROOT, force_asr: bool = False, metadata_override: dict[str, Any] | None = None) -> dict[str, Any]:
    artifact_root = Path(artifact_root).resolve()
    artifact_root.mkdir(parents=True, exist_ok=True)
    url = video["url"]
    video_id = video["video_id"]
    base = artifact_root / video_id
    metadata = metadata_override or _metadata(url, video)
    title = metadata.get("title") or video.get("title") or video_id
    channel = metadata.get("channel") or metadata.get("uploader") or video.get("channel") or "UNKNOWN"
    content_hash = hashlib.sha256(json.dumps({k: metadata.get(k) for k in ("id", "title", "description", "duration", "upload_date")}, sort_keys=True, default=str).encode()).hexdigest()
    existing = base.with_suffix(".metadata.json")
    research_question = str(video.get("research_question") or video.get("question") or "default_content_review")
    channel_id = video.get("channel_id") or metadata.get("channel_id")
    first_seen_at = (json.loads(existing.read_text()).get("first_seen_at") if existing.exists() else None)
    if existing.exists():
        prior = json.loads(existing.read_text())
        # A YouTube video ID is the concrete source identity.  If the video
        # already has a verified local transcript artifact, metadata drift on
        # a later page fetch must not force a second acquisition attempt.
        same_content = prior.get("processing_status") == "FULLY_PROCESSED" and base.with_suffix(".transcript.txt").exists()
        same_question = prior.get("last_research_question") in {None, research_question}
        if same_content and same_question and not force_asr:
            return {"video_id": video_id, "url": url, "title": title, "channel": channel, "channel_id": channel_id,
                    "duplicate_unchanged": True, "duplicate_status": "DUPLICATE_SKIPPED",
                    "novelty_status": "PREVIOUSLY_PROCESSED", "new_artifact_set_created": False,
                    "processing_status": "DUPLICATE_UNCHANGED", "artifact_root": _artifact_ref(artifact_root),
                    "transcript_path": _artifact_ref(base.with_suffix(".transcript.txt")),
                    "content_hash": content_hash, "transcript_hash": prior.get("transcript_hash"),
                    "research_count": int(prior.get("research_count", 1) or 1), "last_researched_at": prior.get("last_researched_at")}
    asr_backend = "NONE"
    asr_diagnostics: dict[str, Any] = {}
    audio_acquired = False
    ffmpeg_normalized = False
    try:
        if force_asr:
            transcript, segments, transcript_source, asr_backend, asr_diagnostics = acquire_audio_asr(url, video_id)
            audio_acquired = True
            ffmpeg_normalized = True
        else:
            if video.get("discovery_method") == "YOUTUBE_RSS":
                transcript, segments, transcript_source = _http_caption_tracks(url, video_id)
            else:
                transcript, segments, transcript_source = acquire_captions(url, video_id)
    except Exception as caption_error:
        try:
            transcript, segments, transcript_source, asr_backend, asr_diagnostics = acquire_audio_asr(url, video_id)
            audio_acquired = True
            ffmpeg_normalized = True
        except Exception as asr_error:
            # Preserve bounded, truthful metadata evidence instead of
            # discarding the objective when both transcript methods fail.
            # This is explicitly incomplete: no transcript or video claim is
            # inferred from the description alone.
            description = re.sub(r"\s+", " ", html.unescape(str(metadata.get("description") or video.get("description") or ""))).strip()
            partial_path = base.with_suffix(".partial-evidence.json")
            partial = {
                "video_id": video_id, "url": url, "title": title, "channel": channel,
                "content_hash": content_hash, "transcript_status": "UNAVAILABLE",
                "caption_failure_reason": str(caption_error), "asr_failure_reason": str(asr_error),
                "processing_status": "PARTIAL_EVIDENCE", "evidence_status": "EVIDENCE_INCOMPLETE",
                "fallback_ladder": ["public captions", "local ASR", "video metadata/description", "independent text source"],
                "fallback_used": "video_metadata_description",
                "description": description[:5000], "claims_from_description": [],
                "key_findings": ["Transcript unavailable; only public metadata/description was preserved."],
                "follow_up_questions": ["Can the material video claims be verified from an independent text source?", "What customer problem or desired outcome is evidenced outside the video?"],
                "research_disposition": "EVIDENCE_INCOMPLETE", "last_processed_at": _now(),
                "alpha_invoked": False, "opportunities_created": 0, "work_orders_created": 0,
            }
            _write_json(partial_path, partial)
            _write_json(existing, partial)
            return {**partial, "new_artifact_set_created": True,
                    "artifact_root": _artifact_ref(artifact_root),
                    "partial_evidence_path": _artifact_ref(partial_path),
                    "executive_summary": partial["key_findings"][0],
                    "structured_data": {"description": description[:5000], "transcript_available": False},
                    "summary_created": True, "extraction_created": True,
                    "scored": False, "provenance_created": True, "stored": True}
    if not transcript:
        raise RuntimeError("caption acquisition returned empty transcript")
    transcript_hash = hashlib.sha256(transcript.encode()).hexdigest()
    novelty_status = "SAME_SOURCE_NEW_QUESTION" if existing.exists() else "NEW"
    prior_count = int(json.loads(existing.read_text()).get("research_count", 0) or 0) if existing.exists() else 0
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
    transcript_reference = _artifact_ref(transcript_path)
    provenance = [{"source_video_id": video_id, "transcript_reference": transcript_reference, "timestamp_or_segment": segment["timestamp"], "extracted_text_or_paraphrase": segment["text"][:500]} for segment in segments[:8]]
    timestamp = _now()
    processing_status = "PARTIAL_EVIDENCE" if asr_diagnostics.get("status") == "PARTIAL_TRANSCRIPT" else "FULLY_PROCESSED"
    metadata_record = {"video_id": video_id, "channel_id": channel_id, "url": url, "channel": channel, "title": title, "source": "yt-dlp public captions" if transcript_source == "public_youtube_captions" else "yt-dlp temporary audio + local ASR", "content_hash": content_hash, "previous_content_hash": (json.loads(existing.read_text()).get("content_hash") if existing.exists() else None), "content_changed": bool(existing.exists() and json.loads(existing.read_text()).get("content_hash") != content_hash), "transcript_status": "ACQUIRED", "transcript_source": transcript_source, "transcript_hash": transcript_hash, "summary_status": "CREATED", "extraction_status": "CREATED", "scoring_status": "SCORED", "processing_status": processing_status, "novelty_status": novelty_status, "duplicate_status": "NEW_OR_UPDATED", "first_seen_at": first_seen_at or timestamp, "first_researched_at": (json.loads(existing.read_text()).get("first_researched_at") if existing.exists() else timestamp), "last_researched_at": timestamp, "last_processed_at": timestamp, "research_count": prior_count + 1, "last_research_question": research_question, "audio_acquired": audio_acquired, "ffmpeg_normalized": ffmpeg_normalized, "asr_backend": asr_backend, "asr_diagnostics": asr_diagnostics, "alpha_invoked": False, "opportunities_created": 0, "work_orders_created": 0}
    _write_json(existing, metadata_record)
    (base.with_suffix(".summary.md")).write_text("\n".join([f"# {title}", "", f"Executive summary: {summary['executive_summary']}", f"Main topic: {summary['main_topic']}", f"Key themes: {', '.join(summary['key_themes'])}", "", "Key points:", *[f"- {x}" for x in summary["key_points"]], "", "Risks or caveats:", *[f"- {x}" for x in summary["risks_or_caveats"]], "", "Unanswered questions:", *[f"- {x}" for x in summary["unanswered_questions"]]]) + "\n")
    _write_json(base.with_suffix(".structured-extraction.json"), extraction)
    _write_json(base.with_suffix(".provenance.json"), {"items": provenance})
    _write_json(base.with_suffix(".scores.json"), score_record)
    return {"video_id": video_id, "channel_id": channel_id, "title": title, "duplicate_unchanged": False, "duplicate_status": "NEW_OR_UPDATED", "novelty_status": novelty_status, "content_changed": bool(existing.exists() and json.loads(existing.read_text()).get("content_hash") != content_hash), "new_artifact_set_created": True, "transcript_acquired": True, "transcript_word_count": len(transcript.split()), "transcript_source": transcript_source, "summary_created": True, "structured_extraction_created": True, "scored": True, "audio_acquired": audio_acquired, "ffmpeg_normalized": ffmpeg_normalized, "asr_backend": asr_backend, "asr_diagnostics": asr_diagnostics, "processing_status": processing_status, "artifact_root": _artifact_ref(artifact_root), "transcript_path": _artifact_ref(transcript_path), "summary_path": _artifact_ref(base.with_suffix('.summary.md')), "structured_extraction_path": _artifact_ref(base.with_suffix('.structured-extraction.json')), "scores_path": _artifact_ref(base.with_suffix('.scores.json')), "content_hash": content_hash, "transcript_hash": transcript_hash, "research_count": prior_count + 1, "last_researched_at": timestamp, "alpha_invoked": False, "opportunities_created": 0, "work_orders_created": 0}


def select_channel_videos(channel_url: str, limit: int) -> list[dict[str, str]]:
    # RSS is the bounded, metadata-only channel path.  It avoids the known
    # yt-dlp Python startup/network hang and never enumerates channel history.
    try:
        return _rss_channel_videos(channel_url, limit)
    except Exception as rss_error:
        result = _run_ytdlp(["yt-dlp", "--no-update", "--no-warnings", "--flat-playlist", "--playlist-end", str(limit), "--dump-single-json", f"{channel_url.rstrip('/')}/videos"])
        if result.returncode != 0:
            raise RuntimeError(f"scheduled selection failed: RSS={rss_error}; yt-dlp={result.stderr[-300:].strip()}") from rss_error
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
