#!/usr/bin/env python3
"""Color-only lip appearance canaries on the original raw MuseTalk motion."""
from __future__ import annotations

import array
import colorsys
import hashlib
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageStat

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "artifacts/nova/identity-preservation/nova_lip_identity_canary_raw.mp4"
SOURCE_AUDIO = ROOT / "artifacts/nova/chattts-canary/nova_chattts_avatar_source.wav"
REFERENCE = ROOT / "assets/nova/avatar/nova_reference.png"
LANDMARKS = ROOT / "artifacts/nova/lip-color-correction/raw_lip_landmarks.jsonl"
OUT = ROOT / "artifacts/nova/lip-color-correction"
FPS = 25
SIZE = (1824, 1376)
REFERENCE_GEOMETRY = ROOT / "assets/nova/avatar/nova_reference_mouth_geometry.json"
CANDIDATES = {
    "A": {"name": "subtle", "profile_mix": 0.40, "texture_blend": 0.00, "texture_blur_radius": 0.0},
    "B": {"name": "balanced", "profile_mix": 0.55, "texture_blend": 0.02, "texture_blur_radius": 0.45},
    "C": {"name": "strongest_nova_match", "profile_mix": 0.70, "texture_blend": 0.05, "texture_blur_radius": 0.55},
}
DESTS = {k: OUT / f"nova_lip_color_{k}.mp4" for k in "ABC"}


def run(args: list[str], *, binary: bool = False) -> bytes | str:
    p = subprocess.run(args, capture_output=True, check=True, timeout=300)
    return p.stdout if binary else p.stdout.decode()


def probe(path: Path) -> dict:
    return json.loads(run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]))


def packet_hash(path: Path, stream: str) -> str:
    b = run(["ffmpeg", "-v", "error", "-i", str(path), "-map", f"0:{stream}:0", "-c", "copy", "-f", "data", "pipe:1"], binary=True)
    return hashlib.sha256(b).hexdigest()


def load_landmarks() -> list[dict]:
    rows = [json.loads(line) for line in LANDMARKS.read_text().splitlines() if line.strip()]
    if not rows or [r["frame"] for r in rows] != list(range(len(rows))):
        raise RuntimeError("landmark_frame_indices_missing_or_nonsequential")
    valid = [r for r in rows if len(r.get("outer_lips", [])) >= 8 and len(r.get("inner_lips", [])) >= 4]
    if len(valid) != len(rows):
        raise RuntimeError(f"lip_landmarks_missing_frames:{len(rows)-len(valid)}")
    return rows


def polygon_mask(size: tuple[int, int], points: list[list[float]]) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).polygon([(round(x), round(y)) for x, y in points], fill=255)
    return mask


def ref_profile(ref: Image.Image, geo: dict) -> dict:
    r = geo["reference"]
    outer = polygon_mask(ref.size, r["outer_lip_contour_px"])
    inner = polygon_mask(ref.size, r["inner_lip_contour_px"])
    ring = ImageChops.subtract(outer, inner)
    pix = ref.load(); maskpx = ring.load()
    mid = r["mouth_center_px"][1]
    h_samples: dict[str, list[float]] = {"upper": [], "lower": []}
    s_samples: dict[str, list[float]] = {"upper": [], "lower": []}
    v_samples: dict[str, list[float]] = {"upper": [], "lower": []}
    for y in range(max(0, int(r["outer_lip_bounds_px"]["top"])), min(ref.height, math.ceil(r["outer_lip_bounds_px"]["bottom"]))):
        for x in range(max(0, int(r["outer_lip_bounds_px"]["left"])), min(ref.width, math.ceil(r["outer_lip_bounds_px"]["right"]))):
            if maskpx[x, y] < 128:
                continue
            name = "upper" if y < mid else "lower"
            h, s, v = colorsys.rgb_to_hsv(*(c / 255 for c in pix[x, y]))
            h_samples[name].append(h); s_samples[name].append(s); v_samples[name].append(v)
    out = {}
    for side in ("upper", "lower"):
        out[side] = {"hue_median": median(h_samples[side]), "saturation_median": median(s_samples[side]),
                     "value_median": median(v_samples[side]), "sample_count": len(h_samples[side])}
    return out


def measured_frame_profile(image: Image.Image, row: dict) -> dict:
    m=ring_mask(row,image.size).load(); pixels=image.load()
    ys=[p[1] for p in row["outer_lips"]]; split=(min(ys)+max(ys))/2
    vals={side:{"h":[],"s":[],"v":[]} for side in ("upper","lower")}
    for y in range(max(0,int(min(ys))),min(image.height,math.ceil(max(ys))+1)):
        side="upper" if y<split else "lower"
        for x in range(max(0,int(min(p[0] for p in row["outer_lips"]))),min(image.width,math.ceil(max(p[0] for p in row["outer_lips"]))+1)):
            if m[x,y]<128: continue
            h,s,v=colorsys.rgb_to_hsv(*(c/255 for c in pixels[x,y]))
            vals[side]["h"].append(h);vals[side]["s"].append(s);vals[side]["v"].append(v)
    return {side:{"hue_median":median(v["h"]),"saturation_median":median(v["s"]),"value_median":median(v["v"])} for side,v in vals.items()}


def color_profile_distance(actual: dict, target: dict) -> float:
    distances=[]
    for side in ("upper","lower"):
        a=actual[side];t=target[side]
        distances.append(abs(circular_hue_delta(a["hue_median"],t["hue_median"])) + abs(a["saturation_median"]-t["saturation_median"]) + abs(a["value_median"]-t["value_median"]))
    return sum(distances)/len(distances)


def ring_mask(row: dict, frame_size: tuple[int, int]) -> Image.Image:
    outer = polygon_mask(frame_size, row["outer_lips"])
    inner = polygon_mask(frame_size, row["inner_lips"])
    # The frame-specific inner lip polygon is excluded, protecting teeth,
    # tongue and cavity. This mask selects color-only pixels; it never paints
    # from the approved image or supplies an output mouth shape.
    ring = ImageChops.subtract(outer, inner)
    # 1.2 px feather to soften the color edge, clamped to the lip ring itself.
    soft = ring.filter(ImageFilter.GaussianBlur(radius=1.2))
    return ImageChops.multiply(ring, soft)


def circular_hue_delta(source: float, target: float) -> float:
    return (target - source + 0.5) % 1.0 - 0.5


def recolor_frame(frame: Image.Image, row: dict, target: dict, config: dict) -> Image.Image:
    mask = ring_mask(row, frame.size)
    # Texture softening is sampled only inside the moving lip ring. Pixels
    # outside that ring remain the original decoded MuseTalk pixels.
    original = frame
    softened = frame.filter(ImageFilter.GaussianBlur(radius=config["texture_blur_radius"])) if config["texture_blend"] else frame
    src = original.load(); soft = softened.load(); mp = mask.load()
    out = original.copy(); dst = out.load()
    xs = [p[0] for p in row["outer_lips"]]; ys = [p[1] for p in row["outer_lips"]]
    x0=max(0,int(min(xs))-2); x1=min(frame.width,int(max(xs))+3)
    y0=max(0,int(min(ys))-2); y1=min(frame.height,int(max(ys))+3)
    split=(min(ys)+max(ys))/2
    mix=float(config["profile_mix"])
    frame_stats={side:{"h":[],"s":[],"v":[]} for side in ("upper","lower")}
    for y in range(y0,y1):
        side="upper" if y<split else "lower"
        for x in range(x0,x1):
            if mp[x,y] < 128: continue
            h,s,v=colorsys.rgb_to_hsv(*(c/255 for c in src[x,y]))
            frame_stats[side]["h"].append(h);frame_stats[side]["s"].append(s);frame_stats[side]["v"].append(v)
    frame_medians={side:{k:median(v) for k,v in data.items()} for side,data in frame_stats.items()}
    for y in range(y0,y1):
        side="upper" if y < split else "lower"
        t=target[side]
        for x in range(x0,x1):
            alpha=mp[x,y]/255
            if alpha <= 0:
                continue
            source=tuple(round(a*(1-config["texture_blend"])+b*config["texture_blend"]) for a,b in zip(src[x,y],soft[x,y]))
            rr,gg,bb=(z/255 for z in source)
            h,s,v=colorsys.rgb_to_hsv(rr,gg,bb)
            # Shift the region's median color while preserving each pixel's
            # hue/saturation/brightness variation and highlight structure.
            src_med=frame_medians[side]
            h=(h + mix*circular_hue_delta(src_med["h"],t["hue_median"]))%1.0
            s=max(0.0,min(1.0,s + mix*(t["saturation_median"]-src_med["s"])))
            value_ratio=t["value_median"]/max(0.05,src_med["v"])
            v=max(0.0,min(1.0,v*(value_ratio**(mix*0.30))))
            nr,ng,nb=colorsys.hsv_to_rgb(h,s,v)
            corrected=(round(nr*255),round(ng*255),round(nb*255))
            dst[x,y]=tuple(round(a*(1-alpha)+b*alpha) for a,b in zip(src[x,y],corrected))
    return out


def make_candidate(key: str, rows: list[dict], profile: dict) -> dict:
    output=DESTS[key]; cfg=CANDIDATES[key]
    if output.exists(): raise FileExistsError(f"refusing_to_overwrite:{output}")
    raw=run(["ffmpeg","-v","error","-i",str(RAW),"-an","-vsync","0","-f","rawvideo","-pix_fmt","rgb24","pipe:1"],binary=True)
    frame_bytes=SIZE[0]*SIZE[1]*3
    if len(raw)%frame_bytes or len(raw)//frame_bytes!=len(rows):
        raise RuntimeError(f"decoded_frame_count_mismatch:{len(raw)//frame_bytes}/{len(rows)}")
    proc=subprocess.Popen(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","rawvideo","-pix_fmt","rgb24","-s:v",f"{SIZE[0]}x{SIZE[1]}","-r",str(FPS),"-i","pipe:0","-i",str(RAW),"-map","0:v:0","-map","1:a:0","-r",str(FPS),"-c:v","libx264","-preset","medium","-crf","17","-pix_fmt","yuv420p","-c:a","copy",str(output)],stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for i,row in enumerate(rows):
            frame=Image.frombytes("RGB",SIZE,raw[i*frame_bytes:(i+1)*frame_bytes])
            fixed=recolor_frame(frame,row,profile,cfg)
            proc.stdin.write(fixed.tobytes())
        proc.stdin.close(); err=proc.stderr.read().decode(errors="replace")
        rc=proc.wait()
        if rc: raise RuntimeError("candidate_encode_failed:"+err[-500:])
    finally:
        if proc.poll() is None: proc.kill();proc.wait()
    return {"provider":"local color-only postprocess","model":"moving Vision lip ring + HSV profile transfer",
            "config":cfg,"frames":len(rows),"file_size_bytes":output.stat().st_size,
            "sha256":hashlib.sha256(output.read_bytes()).hexdigest(),"audio_packet_sha256":packet_hash(output,"a"),
            "video_packet_sha256":packet_hash(output,"v")}


def existing_candidate_metadata(key: str) -> dict:
    output=DESTS[key]
    pp=probe(output)
    v=next(s for s in pp["streams"] if s["codec_type"]=="video")
    if int(v.get("nb_frames",0)) != 169 or v["r_frame_rate"] != "25/1":
        raise RuntimeError(f"existing_candidate_is_not_our_expected_render:{output}")
    return {"provider":"local color-only postprocess","model":"moving Vision lip ring + HSV profile transfer",
            "config":CANDIDATES[key],"frames":169,"file_size_bytes":output.stat().st_size,
            "sha256":hashlib.sha256(output.read_bytes()).hexdigest(),"audio_packet_sha256":packet_hash(output,"a"),
            "video_packet_sha256":packet_hash(output,"v"),"resumed_after_candidate_encode":True}


def main() -> None:
    OUT.mkdir(parents=True,exist_ok=True)
    # Reuse candidates if generation completed but a later reporting step was
    # interrupted; never overwrite an existing output.
    raw_probe=probe(RAW)
    v=next(x for x in raw_probe["streams"] if x["codec_type"]=="video")
    a=next(x for x in raw_probe["streams"] if x["codec_type"]=="audio")
    if (int(v["width"]),int(v["height"]),v["r_frame_rate"],int(v["nb_frames"]))!=(1824,1376,"25/1",169):
        raise RuntimeError("unexpected_motion_ground_truth_video_parameters")
    geo=json.loads(REFERENCE_GEOMETRY.read_text())
    ref=Image.open(REFERENCE).convert("RGB")
    profile=ref_profile(ref,geo)
    rows=load_landmarks()
    if len(rows)!=169: raise RuntimeError("expected_one_dynamic_lip_mask_per_source_frame")
    LANDMARKS.parent.mkdir(parents=True,exist_ok=True)
    profile_record={"schema_version":"nexus.nova.lip-color-profile.v1","created_at":datetime.now(timezone.utc).isoformat(),
                    "reference_image":"assets/nova/avatar/nova_reference.png","method":"median HSV sampled inside approved outer-minus-inner lip contour; appearance target only",
                    "upper_lower_profile":profile,"does_not_supply_pixels_or_geometry":True}
    (OUT/"NOVA_LIP_COLOR_PROFILE.json").write_text(json.dumps(profile_record,indent=2)+"\n")
    results={k:(existing_candidate_metadata(k) if DESTS[k].exists() else make_candidate(k,rows,profile)) for k in "ABC"}
    raw_audio_hash=packet_hash(RAW,"a")
    for k in "ABC":
        pp=probe(DESTS[k]); vv=next(x for x in pp["streams"] if x["codec_type"]=="video"); aa=next(x for x in pp["streams"] if x["codec_type"]=="audio")
        results[k]["sync"]={"fps":vv["r_frame_rate"],"frame_count":int(vv["nb_frames"]),"video_start":float(vv.get("start_time",0)),
                             "audio_start":float(aa.get("start_time",0)),"audio_duration":float(aa["duration"]),
                             "audio_packet_hash_matches_raw":results[k]["audio_packet_sha256"]==raw_audio_hash,
                             "timing_match":vv["r_frame_rate"]==v["r_frame_rate"] and int(vv["nb_frames"])==int(v["nb_frames"]) and abs(float(aa["duration"])-float(a["duration"]))<0.001 and abs(float(aa.get("start_time",0))-float(a.get("start_time",0)))<0.001}
    # A representative speaking-frame comparison, all images use the exact
    # same frame index from the motion ground truth.
    frame_i=60
    frame_bytes=SIZE[0]*SIZE[1]*3
    raw_frames=run(["ffmpeg","-v","error","-i",str(RAW),"-an","-vsync","0","-f","rawvideo","-pix_fmt","rgb24","pipe:1"],binary=True)
    raw_one=raw_frames[frame_i*frame_bytes:(frame_i+1)*frame_bytes]
    tiles=[]
    from PIL import ImageOps, ImageFont
    labels=[("APPROVED NOVA REFERENCE",ref), ("RAW GOOD MUSETALK",Image.frombytes("RGB",SIZE,raw_one))]
    for k in "ABC":
        b=run(["ffmpeg","-v","error","-i",str(DESTS[k]),"-vf",f"select=eq(n\\,{frame_i})","-vsync","0","-frames:v","1","-f","image2pipe","-vcodec","png","pipe:1"],binary=True)
        from io import BytesIO
        candidate_frame=Image.open(BytesIO(b)).convert("RGB")
        raw_profile=measured_frame_profile(Image.frombytes("RGB",SIZE,raw_one),rows[frame_i])
        candidate_profile=measured_frame_profile(candidate_frame,rows[frame_i])
        raw_distance=color_profile_distance(raw_profile,profile)
        candidate_distance=color_profile_distance(candidate_profile,profile)
        results[k]["frame_color_match"]={"frame_index":frame_i,"raw_hsv_profile_distance":round(raw_distance,5),
                                           "candidate_hsv_profile_distance":round(candidate_distance,5),
                                           "improved":candidate_distance<raw_distance,
                                           "measurement":"mean per-side median HSV distance to approved reference lip color profile"}
        labels.append((f"COLOR {k}",candidate_frame))
    mouth_crop=(740,620,1010,780)
    labels=[(name,img.crop(mouth_crop)) for name,img in labels]
    tw,th=456,270
    sheet=Image.new("RGB",(tw*5,th+32),(245,245,245)); draw=ImageDraw.Draw(sheet)
    for i,(label,img) in enumerate(labels):
        thumb=ImageOps.fit(img,(tw,th),method=Image.Resampling.LANCZOS,centering=(0.5,0.53))
        sheet.paste(thumb,(i*tw,32)); draw.text((i*tw+8,9),label,fill=(15,15,15))
    (OUT/"lip_color_comparison.png").parent.mkdir(parents=True,exist_ok=True)
    sheet.save(OUT/"lip_color_comparison.png")
    manifest={"schema_version":"nexus.nova.lip-color-canaries.v1","created_at":datetime.now(timezone.utc).isoformat(),
              "motion_ground_truth":str(RAW.relative_to(ROOT)),"source_audio_wav":str(SOURCE_AUDIO.relative_to(ROOT)),
              "source_audio_is_muxed_as_aac_in_motion_ground_truth":True,"reference":"assets/nova/avatar/nova_reference.png",
              "reference_color_profile":profile_record,"motion_geometry_frozen":True,"timing_frozen":True,
              "inner_mouth_untouched_by_mask_and_color_transform":True,"frame_count":len(rows),"fps":FPS,
              "source_audio_packet_sha256":raw_audio_hash,"comparison_frame_index":frame_i,"candidates":results,
              "mask_rule":"frame-specific Vision outer_lips polygon minus inner_lips polygon; 1.2px color feather clamped inside lip ring; no reference pixels composited",
              "forbidden_geometry_operations_used":False}
    (OUT/"NOVA_LIP_COLOR_CANDIDATES.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    print(json.dumps(manifest,indent=2))


if __name__=="__main__":main()
