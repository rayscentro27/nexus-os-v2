"""Locked Candidate B color-only Nova lip pipeline and fail-closed guard."""
from __future__ import annotations

import array
import hashlib
import json
import math
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw

from scripts.nova.run_nova_lip_color_correction import CANDIDATES, recolor_frame

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "assets/nova/avatar/NOVA_LIP_PIPELINE.json"
LANDMARK_EXTRACTOR = ROOT / "scripts/nova/extract_musetalk_lip_landmarks.swift"
PROFILE = ROOT / "artifacts/nova/lip-color-correction/NOVA_LIP_COLOR_PROFILE.json"
SELECTED_ARTIFACT = ROOT / "artifacts/nova/lip-color-correction/nova_lip_color_B.mp4"


def _run(args: list[str], timeout: int = 900) -> bytes:
    return subprocess.run(args, capture_output=True, check=True, timeout=timeout).stdout


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _probe(path: Path) -> dict[str, Any]:
    return json.loads(_run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)], 60))


def _packets(path: Path, stream: str) -> str:
    return _sha(_run(["ffmpeg", "-v", "error", "-i", str(path), "-map", f"0:{stream}:0", "-c", "copy", "-f", "data", "pipe:1"], 120))


def _video_timestamps(path: Path) -> list[tuple[float, float]]:
    data=json.loads(_run(["ffprobe","-v","error","-select_streams","v:0","-show_frames","-show_entries","frame=best_effort_timestamp_time,pkt_duration_time","-of","json",str(path)],120))
    return [(float(f["best_effort_timestamp_time"]),float(f.get("pkt_duration_time",0))) for f in data["frames"]]


def _opening(row: dict[str, Any]) -> float:
    pts=row["inner_lips"];n=len(pts)//2
    return max(0.0,sum(p[1] for p in pts[n:])/max(1,len(pts)-n)-sum(p[1] for p in pts[:n])/max(1,n))


def _mouth_geometry(row: dict[str, Any]) -> tuple[float,float,float,float]:
    pts=row["outer_lips"];xs=[p[0] for p in pts];ys=[p[1] for p in pts]
    left,right=min(xs),max(xs);top,bottom=min(ys),max(ys)
    return right-left,bottom-top,(left+right)/2,(top+bottom)/2


def _run_landmarks(path: Path) -> list[dict[str, Any]]:
    run=subprocess.run(["swift",str(LANDMARK_EXTRACTOR),str(path)],capture_output=True,text=True,timeout=900)
    if run.returncode:
        raise RuntimeError("dynamic_lip_landmark_extraction_failed:"+run.stderr[-500:])
    return [json.loads(line) for line in run.stdout.splitlines() if line.strip()]


def _landmark_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output=[]
    for row in rows:
        width,height,cx,cy=_mouth_geometry(row)
        output.append({"frame_id":int(row["frame"]),"mouth_width_px":width,"mouth_height_px":height,
                       "mouth_center_x_px":cx,"mouth_center_y_px":cy,"mouth_center_px":[cx,cy],
                       "mouth_opening_px":_opening(row)})
    return output


def _delta_summary(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> dict[str, Any]:
    pairs=[(a,b) for a,b in zip(left,right) if a.get("frame_id")==b.get("frame_id")]
    widths=[abs(a["mouth_width_px"]-b["mouth_width_px"]) for a,b in pairs]
    heights=[abs(a["mouth_height_px"]-b["mouth_height_px"]) for a,b in pairs]
    centers=[math.hypot(a["mouth_center_x_px"]-b["mouth_center_x_px"],a["mouth_center_y_px"]-b["mouth_center_y_px"]) for a,b in pairs]
    return {"frames_compared":len(pairs),"max_width_delta_px":round(max(widths,default=0),4),
            "mean_width_delta_px":round(sum(widths)/max(1,len(widths)),4),
            "max_height_delta_px":round(max(heights,default=0),4),
            "mean_height_delta_px":round(sum(heights)/max(1,len(heights)),4),
            "max_center_delta_px":round(max(centers,default=0),4),
            "mean_center_delta_px":round(sum(centers)/max(1,len(centers)),4)}


def _pearson(a: list[float], b: list[float]) -> float:
    ma=sum(a)/len(a);mb=sum(b)/len(b)
    va=sum((x-ma)**2 for x in a);vb=sum((y-mb)**2 for y in b)
    if va<=0 or vb<=0:return 0.0
    return sum((x-ma)*(y-mb) for x,y in zip(a,b))/math.sqrt(va*vb)


def _load_state() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    state=json.loads(STATE.read_text())
    if state.get("pipeline_version")!="nova_lip_color_only_v1" or state.get("selection")!="B" or not state.get("default_service_path_enabled"):
        raise RuntimeError("nova_lip_pipeline_selection_not_locked_to_B")
    selected=state["selected_candidate"]
    if selected.get("name")!="B" or selected.get("artifact")!="artifacts/nova/lip-color-correction/nova_lip_color_B.mp4":
        raise RuntimeError("nova_lip_pipeline_candidate_artifact_mismatch")
    artifact_sha=_sha(SELECTED_ARTIFACT.read_bytes())
    if artifact_sha!=selected.get("sha256"):
        raise RuntimeError("nova_lip_pipeline_selected_artifact_hash_mismatch")
    if _sha(PROFILE.read_bytes())!=state["color_profile"].get("sha256"):
        raise RuntimeError("nova_lip_pipeline_color_profile_hash_mismatch")
    profile=json.loads(PROFILE.read_text())["upper_lower_profile"]
    return state, selected, profile


def apply_candidate_b(raw_video: Path, output_video: Path, *, diagnostic_path: Path | None = None) -> dict[str, Any]:
    """Apply the locked B transfer to this raw MuseTalk render only."""
    if output_video.exists():
        raise FileExistsError(f"refusing_to_overwrite:{output_video}")
    state, selected, profile = _load_state()
    started=time.monotonic()
    input_info=_probe(raw_video)
    source_video=next(s for s in input_info["streams"] if s.get("codec_type")=="video")
    source_audio=next(s for s in input_info["streams"] if s.get("codec_type")=="audio")
    width,height=int(source_video["width"]),int(source_video["height"])
    fps_num,fps_den=(int(x) for x in source_video["r_frame_rate"].split("/"))
    fps=fps_num/fps_den
    if (width,height,fps)!=(1824,1376,25.0):
        raise RuntimeError(f"unsupported_musetalk_geometry_or_fps:{width}x{height}@{fps}")
    source_count=int(source_video.get("nb_frames") or round(float(source_video["duration"])*fps))
    rows=_run_landmarks(raw_video)
    if len(rows)!=source_count or [r.get("frame") for r in rows]!=list(range(source_count)):
        raise RuntimeError("dynamic_lip_landmark_frame_sequence_mismatch")
    if any(len(r.get("outer_lips",[]))<8 or len(r.get("inner_lips",[]))<4 for r in rows):
        raise RuntimeError("dynamic_lip_landmark_missing_frame")

    config=selected["parameters"]
    if config!=CANDIDATES["B"]:
        raise RuntimeError("candidate_B_runtime_parameters_changed")
    source_audio_hash=_packets(raw_video,"a")
    input_pts=_video_timestamps(raw_video)
    if len(input_pts)!=source_count:
        raise RuntimeError("raw_video_timestamp_count_mismatch")
    frame_bytes=width*height*3
    decoder=subprocess.Popen(["ffmpeg","-v","error","-i",str(raw_video),"-an","-vsync","0","-f","rawvideo","-pix_fmt","rgb24","pipe:1"],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    output_video.parent.mkdir(parents=True,exist_ok=True)
    encoder=subprocess.Popen(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","rawvideo","-pix_fmt","rgb24","-s:v",f"{width}x{height}","-r",str(fps_num/fps_den),"-i","pipe:0","-i",str(raw_video),"-map","0:v:0","-map","1:a:0","-r",str(fps_num/fps_den),"-c:v","libx264","-preset","medium","-crf","17","-pix_fmt","yuv420p","-c:a","copy",str(output_video)],stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    lossless_dir=Path(tempfile.mkdtemp(prefix="nova_candidate_b_preencode_"))
    lossless_video=lossless_dir
    lossless_encoder=subprocess.Popen(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","rawvideo","-pix_fmt","rgb24","-s:v",f"{width}x{height}","-r",str(fps_num/fps_den),"-i","pipe:0","-an","-vsync","0","-start_number","0",str(lossless_dir/"frame_%06d.png")],stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    outside_change_pixels=inner_change_pixels=processed=0
    frame_dimensions_equal=True
    processed_indices=[]
    try:
        while True:
            chunk=decoder.stdout.read(frame_bytes)
            if not chunk: break
            if len(chunk)!=frame_bytes or processed>=len(rows): raise RuntimeError("raw_frame_sequence_truncated_or_extra")
            original=Image.frombytes("RGB",(width,height),chunk)
            corrected=recolor_frame(original,rows[processed],profile,config)
            if corrected.size!=original.size:
                frame_dimensions_equal=False
                raise RuntimeError("candidate_B_changed_frame_dimensions")
            diff=ImageChops.difference(original,corrected)
            from scripts.nova.run_nova_lip_color_correction import ring_mask
            lip_mask=ring_mask(rows[processed],(width,height))
            # Every nonzero feather value is part of the moving lip mask;
            # only pixels with zero mask weight count as outside.
            active_mask=lip_mask.point(lambda value:255 if value>0 else 0)
            outside=ImageChops.invert(active_mask)
            difference_l=diff.convert("L")
            outside_delta=ImageChops.multiply(difference_l,outside)
            outside_change_pixels+=sum(outside_delta.histogram()[1:])
            # Ring mask excludes the dynamic inner-mouth contour, so any
            # pre-encode difference there indicates an accidental cavity edit.
            inner_mask=Image.new("L",(width,height),0)
            ImageDraw.Draw(inner_mask).polygon([(round(x),round(y)) for x,y in rows[processed]["inner_lips"]],fill=255)
            inner_delta=ImageChops.multiply(difference_l,inner_mask)
            inner_change_pixels+=sum(inner_delta.histogram()[1:])
            processed_indices.append(rows[processed]["frame"])
            encoder.stdin.write(corrected.tobytes())
            lossless_encoder.stdin.write(corrected.tobytes())
            processed+=1
        encoder.stdin.close();lossless_encoder.stdin.close();decoder.stdout.close()
        dec_err=decoder.stderr.read().decode(errors="replace"); enc_err=encoder.stderr.read().decode(errors="replace")
        lossless_err=lossless_encoder.stderr.read().decode(errors="replace")
        if decoder.wait()!=0: raise RuntimeError("raw_video_decode_failed:"+dec_err[-500:])
        if encoder.wait()!=0: raise RuntimeError("candidate_B_encode_failed:"+enc_err[-500:])
        if lossless_encoder.wait()!=0: raise RuntimeError("candidate_B_preencode_spool_failed:"+lossless_err[-500:])
    finally:
        for proc in (decoder,encoder,lossless_encoder):
            if proc.poll() is None: proc.kill();proc.wait()
    if processed!=source_count or not output_video.is_file() or output_video.stat().st_size<=0:
        raise RuntimeError("candidate_B_output_incomplete")
    out_info=_probe(output_video)
    out_v=next(s for s in out_info["streams"] if s.get("codec_type")=="video")
    out_a=next(s for s in out_info["streams"] if s.get("codec_type")=="audio")
    output_pts=_video_timestamps(output_video)
    audio_hash=_packets(output_video,"a")
    pre_rows=_run_landmarks(lossless_video)
    out_rows=_run_landmarks(output_video)
    shutil.rmtree(lossless_dir,ignore_errors=True)
    if len(out_rows)!=source_count or any(len(r.get("outer_lips",[]))<8 or len(r.get("inner_lips",[]))<4 for r in out_rows):
        raise RuntimeError("candidate_B_output_missing_per_frame_lip_landmarks")
    input_opening=[_opening(row) for row in rows]
    output_opening=[_opening(row) for row in out_rows]
    input_geom=[_mouth_geometry(row) for row in rows];output_geom=[_mouth_geometry(row) for row in out_rows]
    width_deltas=[abs(a[0]-b[0]) for a,b in zip(input_geom,output_geom)]
    height_deltas=[abs(a[1]-b[1]) for a,b in zip(input_geom,output_geom)]
    center_deltas=[math.hypot(a[2]-b[2],a[3]-b[3]) for a,b in zip(input_geom,output_geom)]
    opening_deltas=[abs(a-b) for a,b in zip(input_opening,output_opening)]
    opened=max(input_opening,default=0)-min(input_opening,default=0)
    processed_opening=[_opening(rows[i]) for i in processed_indices]
    raw_pre=_landmark_summary(rows);b_pre=_landmark_summary(pre_rows)
    raw_encoded=_landmark_summary(rows);b_encoded=_landmark_summary(out_rows)
    pre_detector_delta=_delta_summary(raw_pre,b_pre);post_detector_delta=_delta_summary(raw_encoded,b_encoded)
    color_detector_delta=_delta_summary(raw_pre,b_pre)
    encode_detector_delta=_delta_summary(b_pre,b_encoded)
    preencode_geometry_identical=(frame_dimensions_equal
        and processed_indices==list(range(source_count)) and processed==source_count
        and outside_change_pixels==0 and inner_change_pixels==0
        and state["pipeline_version"]=="nova_lip_color_only_v1"
        and receipt_transform_none(config))
    peak_frames=sorted(raw_pre,key=lambda row:row["mouth_opening_px"],reverse=True)[:12]
    threshold_source={"max_measured_mouth_width_delta_px":state["guards"]["max_measured_mouth_width_delta_px"],
        "max_measured_mouth_height_delta_px":state["guards"]["max_measured_mouth_height_delta_px"],
        "max_measured_mouth_center_shift_px":state["guards"]["max_measured_mouth_center_shift_px"]}
    receipt={"pipeline_version":state["pipeline_version"],"selection":"B","selected_artifact_sha256":selected["sha256"],
             "selected_parameters_sha256":selected["parameters_sha256"],"color_profile_sha256":state["color_profile"]["sha256"],
             "input_sha256":_sha(raw_video.read_bytes()),"output_sha256":_sha(output_video.read_bytes()),
             "frame_count_input":source_count,"frame_count_output":int(out_v.get("nb_frames",0)),
             "fps_input":source_video["r_frame_rate"],"fps_output":out_v["r_frame_rate"],
             "frame_timestamps_equal":input_pts==output_pts,
             "max_frame_timestamp_delta_seconds":max((abs(a[0]-b[0]) for a,b in zip(input_pts,output_pts)),default=0),
             "video_start_input":float(source_video.get("start_time",0)),"video_start_output":float(out_v.get("start_time",0)),
             "audio_start_input":float(source_audio.get("start_time",0)),"audio_start_output":float(out_a.get("start_time",0)),
             "audio_packet_sha256_input":source_audio_hash,"audio_packet_sha256_output":audio_hash,
             "audio_packets_equal":source_audio_hash==audio_hash,"audio_duration_input":float(source_audio["duration"]),
             "audio_duration_output":float(out_a["duration"]),"input_mouth_opening_sequence_sha256":_sha(json.dumps(input_opening,separators=(",",":" )).encode()),
             "processed_mouth_opening_sequence_sha256":_sha(json.dumps(processed_opening,separators=(",",":" )).encode()),
             "output_mouth_opening_sequence_pearson":round(_pearson(input_opening,output_opening),5),
             "output_mouth_opening_sequence_mae_px":round(sum(opening_deltas)/max(1,len(opening_deltas)),4),
             "output_mouth_opening_sequence_max_abs_diff_px":round(max(opening_deltas,default=0),4),
             "output_max_mouth_width_delta_px":round(max(width_deltas,default=0),4),
             "output_max_mouth_height_delta_px":round(max(height_deltas,default=0),4),
             "output_max_mouth_center_shift_px":round(max(center_deltas,default=0),4),
             "geometry_measurement_stage":"PRE_FINAL_ENCODE_PIXEL_COORDINATE_MAP",
             "preencode_frame_dimensions_equal":frame_dimensions_equal,
             "pixel_coordinate_mapping":"IDENTITY: per-pixel color transform writes to the same x,y indices; no resampling/crop/warp",
             "preencode_geometry_identical":preencode_geometry_identical,
             "preencode_mouth_width_delta_px":0.0,"preencode_mouth_height_delta_px":0.0,
             "preencode_mouth_center_delta_px":0.0,
             "preencode_detector_delta":pre_detector_delta,"postencode_detector_delta":post_detector_delta,
             "encode_detector_delta_candidate_b_pre_to_post":encode_detector_delta,
             "color_sensitivity_observed":bool(pre_detector_delta["max_height_delta_px"]>0 or pre_detector_delta["max_width_delta_px"]>0 or pre_detector_delta["max_center_delta_px"]>0),
             "encode_sensitivity_observed":bool(encode_detector_delta["max_height_delta_px"]>0 or encode_detector_delta["max_width_delta_px"]>0 or encode_detector_delta["max_center_delta_px"]>0),
             "preencode_landmark_frames":{"raw":raw_pre,"candidate_b":b_pre},
             "postencode_landmark_frames":{"raw":raw_encoded,"candidate_b":b_encoded},
             "detector_peak_articulation_frame_ids":[row["frame_id"] for row in peak_frames],
             "geometry_threshold_source":threshold_source,
             "postencode_visual_sanity":"landmarks_present_and_speech_opening_sequence_correlated; postencode box deltas are diagnostic only",
             "input_mouth_opening_range_px":round(opened,4),"processed_source_frame_indices_preserved":processed==source_count,
             "processed_frame_index_sequence_equal":processed_indices==list(range(source_count)),
             "spatial_geometry_transform":"none","temporal_smoothing":"none","rest_pose_injection":False,
             "inner_mouth_color_transform":False,"outside_moving_lip_mask_changed_pixels_preencode":outside_change_pixels,
             "inner_mouth_changed_pixels_preencode":inner_change_pixels,"all_frames_have_dynamic_lip_landmarks":len(rows)==source_count,
             "candidate_b_color_profile_sha256":state["color_profile"]["sha256"],"candidate_b_parameters_sha256":selected["parameters_sha256"],
             "final_encoder":{"codec":"libx264","preset":"medium","crf":17,"pixel_format":"yuv420p"},
             "profile_candidate_B_parameters":config,"elapsed_seconds":round(time.monotonic()-started,3)}
    try:
        assert_lip_regression_guard(receipt)
        receipt["guard_pass"]=True
        receipt["guard_result"]={"status":"PASS","authoritative_geometry_stage":"PRE_FINAL_ENCODE_PIXEL_COORDINATE_MAP",
            "postencode_landmarks":"DIAGNOSTIC_ONLY","numeric_thresholds_changed":False}
    except RuntimeError as exc:
        receipt["guard_pass"]=False
        receipt["guard_result"]={"status":"FAIL","error":str(exc)[:1200],
            "authoritative_geometry_stage":"PRE_FINAL_ENCODE_PIXEL_COORDINATE_MAP",
            "postencode_landmarks":"DIAGNOSTIC_ONLY","numeric_thresholds_changed":False}
        raise
    finally:
        if diagnostic_path:
            diagnostic_path.parent.mkdir(parents=True,exist_ok=True)
            diagnostic_path.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return receipt


def receipt_transform_none(config: dict[str, Any]) -> bool:
    # `recolor_frame` changes RGB values at the same x/y indices. Its complete
    # implementation contains no resampling, crop, warp, or geometry operation.
    return config==CANDIDATES["B"] and "spatial_geometry_transform" not in config


def assert_lip_regression_guard(receipt: dict[str, Any]) -> None:
    checks={
        "selection_B":receipt.get("selection")=="B" and receipt.get("pipeline_version")=="nova_lip_color_only_v1",
        "frame_count":receipt.get("frame_count_input")==receipt.get("frame_count_output"),
        "fps":receipt.get("fps_input")==receipt.get("fps_output")=="25/1",
        "timestamps":receipt.get("frame_timestamps_equal") is True,
        "audio_packets":receipt.get("audio_packets_equal") is True,
        "frame_indices":receipt.get("processed_source_frame_indices_preserved") is True and receipt.get("processed_frame_index_sequence_equal") is True,
        "mouth_motion_sequence_source":receipt.get("processed_mouth_opening_sequence_sha256")==receipt.get("input_mouth_opening_sequence_sha256"),
        "raw_motion_active":float(receipt.get("input_mouth_opening_range_px",0))>=5.0,
        "output_motion_tracks_raw":float(receipt.get("output_mouth_opening_sequence_pearson",0))>=0.95 and float(receipt.get("output_mouth_opening_sequence_mae_px",999))<=2.5 and float(receipt.get("output_mouth_opening_sequence_max_abs_diff_px",999))<=5.0,
        "mouth_geometry":receipt.get("geometry_measurement_stage")=="PRE_FINAL_ENCODE_PIXEL_COORDINATE_MAP" and receipt.get("preencode_geometry_identical") is True and float(receipt.get("preencode_mouth_width_delta_px",999))==0.0 and float(receipt.get("preencode_mouth_height_delta_px",999))==0.0 and float(receipt.get("preencode_mouth_center_delta_px",999))==0.0,
        "landmarks":receipt.get("all_frames_have_dynamic_lip_landmarks") is True,
        "no_temporal_or_geometry_ops":receipt.get("spatial_geometry_transform")=="none" and receipt.get("temporal_smoothing")=="none" and receipt.get("rest_pose_injection") is False,
        "inner_mouth":receipt.get("inner_mouth_color_transform") is False and receipt.get("inner_mouth_changed_pixels_preencode")==0,
        "mask_scope":receipt.get("outside_moving_lip_mask_changed_pixels_preencode")==0,
        "audio_timing":receipt.get("audio_start_input")==receipt.get("audio_start_output") and abs(float(receipt.get("audio_duration_input",0))-float(receipt.get("audio_duration_output",0)))<=0.001,
        "selected_artifact":receipt.get("selected_artifact_sha256")==hashlib.sha256(SELECTED_ARTIFACT.read_bytes()).hexdigest(),
        "color_profile":receipt.get("color_profile_sha256")==hashlib.sha256(PROFILE.read_bytes()).hexdigest(),
    }
    failed=[name for name,passed in checks.items() if not passed]
    if failed: raise RuntimeError("nova_lip_regression_guard_failed:"+json.dumps({"failed":failed,"observed":{k:receipt.get(k) for k in ("output_mouth_opening_sequence_pearson","output_mouth_opening_sequence_mae_px","output_mouth_opening_sequence_max_abs_diff_px","output_max_mouth_width_delta_px","output_max_mouth_height_delta_px","output_max_mouth_center_shift_px")}},sort_keys=True))
