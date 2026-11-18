#!/usr/bin/env python3
"""Bounded LivePortrait resampling/encode comparison; never updates service defaults."""
from __future__ import annotations

import hashlib, importlib.util, json, os, shutil, subprocess, sys, tempfile, time
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
os.environ["MODAL_PROFILE"]="goclearonline"
BASE=ROOT/"artifacts/nova/portrait-renderer"
ANCHOR=ROOT/"artifacts/nova/portrait-renderer-mouth-anchor"
OUT=ROOT/"artifacts/nova/portrait-quality"
SOURCE=BASE/"nova_portrait_speaking_candidate_b.mp4"
CURRENT=ANCHOR/"nova_mouth_anchor_B.mp4"
RECEIPT=BASE/"nova_portrait_speaking_canary.json"
REF_HASH="a0e6a873726ea6831dcc2d8cdbbd603eeaad3324486f7e396c1bd33bb2ee825c"
W,H,FPS,COUNT=1824,1376,25,175

def run(cmd,**kw): return subprocess.run(cmd,check=True,capture_output=True,**kw)
def sha(data): return hashlib.sha256(data).hexdigest()
def probe(p): return json.loads(run(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(p)]).stdout)
def packet_hash(p,selector): return sha(run(["ffmpeg","-v","error","-i",str(p),"-map",selector,"-c","copy","-f","data","pipe:1"]).stdout)
def extract(video,dest):
    dest.mkdir(parents=True,exist_ok=True)
    run(["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(video),"-vsync","0",str(dest/"%06d.png")])
    files=sorted(dest.glob("*.png"))
    if len(files)!=COUNT: raise RuntimeError(f"frame_count:{video}:{len(files)}")
    return files
def encode_frames(frames,silent,crf):
    if silent.exists(): silent.unlink()
    run(["ffmpeg","-hide_banner","-loglevel","error","-y","-framerate",str(FPS),"-i",str(frames/"%06d.png"),"-frames:v",str(COUNT),"-an","-c:v","libx264","-preset","slow","-crf",str(crf),"-pix_fmt","yuv420p",str(silent)])
def mux(silent,audio_src,out):
    run(["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(silent),"-i",str(audio_src),"-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","copy","-movflags","+faststart",str(out)])
from scripts.nexus_agent_platform.provider_enforcement import governed_modal_canary

@governed_modal_canary
def main():
    import modal
    from deploy.modal.nova_portrait_renderer_canary import app,speaking_canary,REFERENCE_SHA256
    if REFERENCE_SHA256!=REF_HASH: raise RuntimeError("reference_pin_changed")
    if OUT.exists(): raise FileExistsError("refusing_to_overwrite_portrait_quality_directory")
    source_probe=probe(SOURCE); current_probe=probe(CURRENT)
    for info in (source_probe,current_probe):
        v=next(s for s in info["streams"] if s.get("codec_type")=="video")
        if (v["width"],v["height"],v["r_frame_rate"],int(v["nb_frames"]))!=(W,H,"25/1",COUNT): raise RuntimeError("input_video_contract_mismatch")
    prior=json.loads(RECEIPT.read_text())
    if not prior["regression"]["candidate_b_guard_pass"] or prior["portrait_renderer"]["driving_multiplier"]!=0.12: raise RuntimeError("current_certification_or_motion_setting_mismatch")
    OUT.mkdir(parents=True)
    work=Path(tempfile.mkdtemp(prefix="nova_portrait_quality_"))
    started=time.monotonic()
    source_frames=work/"source"; target_frames=work/"cubic"; affine_frames=work/"affine"
    try:
        # Candidate A: keep locked geometry and improve only the H.264 encode.
        current_frames=work/"current"; extract(CURRENT,current_frames)
        silent_a=work/"A_silent.mp4"; encode_frames(current_frames,silent_a,14)
        dest_a=OUT/"nova_portrait_quality_A.mp4"; mux(silent_a,CURRENT,dest_a)

        # One same-input, same-motion LivePortrait run changes only paste-back resampling.
        reference=(ROOT/"assets/nova/avatar/nova_reference.png").read_bytes()
        with modal.enable_output(),app.run():
            remote=speaking_canary.remote(SOURCE.read_bytes(),REF_HASH,"cubic")
        model_bytes=remote.pop("model_video_bytes")
        if not model_bytes: raise RuntimeError("missing_cubic_liveportrait_video")
        raw_lp=work/"liveportrait_cubic.mp4"; raw_lp.write_bytes(model_bytes)
        extract(SOURCE,source_frames); extract(raw_lp,target_frames)
        landmark_swift=ROOT/"scripts/nova/extract_nova_face_landmarks.swift"
        lmrun=run(["swift",str(landmark_swift),str(raw_lp)],text=True,timeout=1200)
        new_lm=[json.loads(x) for x in lmrun.stdout.splitlines() if x.strip()]
        src_lm=[json.loads(x) for x in (ANCHOR/"source_face_landmarks.jsonl").read_text().splitlines() if x.strip()]
        if len(new_lm)!=COUNT or len(src_lm)!=COUNT: raise RuntimeError("landmark_count_mismatch")
        util_spec=importlib.util.spec_from_file_location("anchor_util",ROOT/"scripts/nova/run_nova_mouth_anchor_recovery.py")
        util=importlib.util.module_from_spec(util_spec); util_spec.loader.exec_module(util)
        affine_frames.mkdir()
        frame_corr=[]; frame_width=[]
        for i,(sf,tf,sl,tl) in enumerate(zip(sorted(source_frames.glob("*.png")),sorted(target_frames.glob("*.png")),src_lm,new_lm)):
            mat,res=util.affine_fit(util.stable_points(sl),util.stable_points(tl))
            if max(res)>18: raise RuntimeError(f"affine_fit_out_of_bounds:{i}:{max(res)}")
            im1=Image.open(sf).convert("RGB"); im2=Image.open(tf).convert("RGB")
            poly=util.expand_polygon(sl.get("outer_lips") or [],2.0)
            if len(poly)<8: raise RuntimeError(f"missing_lip_roi:{i}")
            result=util.transform_mouth_roi(im1,im2,poly,"B",mat)
            result.save(affine_frames/f"{i+1:06d}.png",compress_level=1)
            im1.close(); im2.close(); result.close()
            frame_corr.append({"affine_fit_max_px":max(res),"frame":i+1})
        silent_b=work/"B_silent.mp4"; encode_frames(affine_frames,silent_b,16)
        silent_c=work/"C_silent.mp4"; encode_frames(affine_frames,silent_c,14)
        dest_b=OUT/"nova_portrait_quality_B.mp4"; dest_c=OUT/"nova_portrait_quality_C.mp4"
        mux(silent_b,SOURCE,dest_b); mux(silent_c,SOURCE,dest_c)
        artifacts={"A":dest_a,"B":dest_b,"C":dest_c}
        expected_audio=packet_hash(CURRENT,"0:a:0")
        checks={}
        for k,p in artifacts.items():
            q=probe(p); v=next(s for s in q["streams"] if s.get("codec_type")=="video")
            checks[k]={"path":str(p.relative_to(ROOT)),"size_bytes":p.stat().st_size,"sha256":sha(p.read_bytes()),
                "frame_count":int(v["nb_frames"]),"fps":v["r_frame_rate"],"dimensions":[v["width"],v["height"]],
                "audio_packets_match":packet_hash(p,"0:a:0")==expected_audio,
                "duration_seconds":float(q["format"]["duration"]),"regression_pass":int(v["nb_frames"])==COUNT and v["r_frame_rate"]=="25/1" and [v["width"],v["height"]]==[W,H] and packet_hash(p,"0:a:0")==expected_audio}
        if not all(c["regression_pass"] for c in checks.values()): raise RuntimeError("quality_candidate_regression_failed")
        receipt={"created_at":datetime.now(timezone.utc).isoformat(),"current_anchor_b_sha256":sha(CURRENT.read_bytes()),
            "input_candidate_b_sha256":sha(SOURCE.read_bytes()),"reference_sha256":REF_HASH,
            "voice_config_unchanged":True,"candidate_b_color_profile_sha256":prior["candidate_b_guard"]["color_profile_sha256"],
            "mouth_anchor_method":"AFFINE_FACE_RELATIVE","mouth_transform_sequence":"per-frame affine from same Candidate B source to cubic LivePortrait non-mouth face landmarks",
            "motion_settings":{"model_revision":prior["portrait_renderer"]["model_revision"],"weights_revision":prior["portrait_renderer"]["weight_revision"],"gpu":"L4","driving_multiplier":0.12,"animation_region":"all","frames":COUNT,"fps":FPS},
            "cubic_modal_run":{k:v for k,v in remote.items() if k!="video_bytes"},
            "candidates":{"A":{"method":"locked affine Candidate B output, re-encoded CRF14","regression":checks["A"]},
                "B":{"method":"same voice/motion, LivePortrait INTER_CUBIC paste-back, affine mouth anchor, CRF16","regression":checks["B"]},
                "C":{"method":"candidate B render plus CRF14 encode","regression":checks["C"]}},
            "affine_fit_max_px_max":max(x["affine_fit_max_px"] for x in frame_corr),
            "elapsed_seconds":round(time.monotonic()-started,3),"selection":"NONE_WAITING_RAY_VISUAL_SELECTION"}
        (OUT/"NOVA_PORTRAIT_QUALITY_DIAGNOSTIC.json").write_text(json.dumps(receipt,indent=2)+"\n")
        print(json.dumps(receipt,indent=2))
    finally:
        shutil.rmtree(work,ignore_errors=True)
if __name__=="__main__": main()
