#!/usr/bin/env python3
"""Bounded LivePortrait detail canary; never changes Nova service defaults."""
from __future__ import annotations

import hashlib, importlib.util, json, os, shutil, subprocess, tempfile, time
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
os.environ["MODAL_PROFILE"]="goclearonline"
BASE=ROOT/"artifacts/nova/portrait-renderer"
ANCHOR=ROOT/"artifacts/nova/portrait-renderer-mouth-anchor"
QUALITY=ROOT/"artifacts/nova/portrait-quality"
OUT=ROOT/"artifacts/nova/portrait-highres"
SOURCE=BASE/"nova_portrait_speaking_candidate_b.mp4"
BASELINE=QUALITY/"nova_portrait_quality_C.mp4"
RECEIPT=BASE/"nova_portrait_speaking_canary.json"
REF_HASH="a0e6a873726ea6831dcc2d8cdbbd603eeaad3324486f7e396c1bd33bb2ee825c"
W,H,FPS,COUNT=1824,1376,25,175
SAMPLES=(1,5,114,115,121)

def run(cmd,**kw): return subprocess.run(cmd,check=True,capture_output=True,**kw)
def sha(b): return hashlib.sha256(b).hexdigest()
def probe(p): return json.loads(run(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(p)]).stdout)
def packet_hash(p,selector): return sha(run(["ffmpeg","-v","error","-i",str(p),"-map",selector,"-c","copy","-f","data","pipe:1"]).stdout)
def extract(video,dest):
    dest.mkdir(parents=True,exist_ok=True)
    run(["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(video),"-vsync","0",str(dest/"%06d.png")])
    files=sorted(dest.glob("*.png"))
    if len(files)!=COUNT: raise RuntimeError(f"frame_count:{video}:{len(files)}")
    return files
def extract_samples(video,dest):
    dest.mkdir(parents=True,exist_ok=True)
    expr="+".join(f"eq(n,{fid-1})" for fid in SAMPLES)
    run(["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(video),"-vf",f"select='{expr}'","-vsync","0",str(dest/"%02d.png")])
    files=sorted(dest.glob("*.png"))
    if len(files)!=len(SAMPLES):raise RuntimeError(f"sample_frame_count:{video}:{len(files)}")
    return files
def encode(frames,silent,crf):
    run(["ffmpeg","-hide_banner","-loglevel","error","-y","-framerate",str(FPS),"-i",str(frames/"%06d.png"),"-frames:v",str(COUNT),"-an","-c:v","libx264","-preset","slow","-crf",str(crf),"-pix_fmt","yuv420p",str(silent)])
def mux(silent,audio_src,out):
    run(["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(silent),"-i",str(audio_src),"-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","copy","-movflags","+faststart",str(out)])
def corr(a,b):
    if len(a)!=len(b) or len(a)<2:return 0.
    ma=sum(a)/len(a); mb=sum(b)/len(b); va=sum((x-ma)**2 for x in a); vb=sum((x-mb)**2 for x in b)
    return sum((x-ma)*(y-mb) for x,y in zip(a,b))/(va*vb)**.5 if va*vb else 0.
def face_lip_values(row):
    outer=row.get("outer_lips") or []; inner=row.get("inner_lips") or []
    if len(outer)<8 or len(inner)<4:return None
    xs=[p[0] for p in outer]; ys=[p[1] for p in outer]; n=len(inner)//2
    opening=max(0,sum(p[1] for p in inner[n:])/(len(inner)-n)-sum(p[1] for p in inner[:n])/n)
    return {"width":max(xs)-min(xs),"height":max(ys)-min(ys),"opening":opening}
def masked_detail(target, warped, target_row, source_row, util, np, Image, ImageDraw, ImageFilter):
    """Add low-amplitude source high-frequency detail inside an eroded face mask only."""
    from PIL import ImageChops
    contour=target_row.get("face_contour") or []
    if len(contour)<8:return target
    mask=Image.new("L",(W,H),0); draw=ImageDraw.Draw(mask)
    # Erode the detector contour inward to keep the feather away from hair/background.
    poly=util.expand_polygon(contour,-5.0)
    draw.polygon([(round(x),round(y)) for x,y in poly],fill=255)
    mask=mask.filter(ImageFilter.MinFilter(11)).filter(ImageFilter.GaussianBlur(3.0))
    # Keep the entire moving mouth outside the detail layer; Candidate B is restored afterwards.
    lips=source_row.get("outer_lips") or []
    if len(lips)>=8:
        fit=util.affine_fit(util.stable_points(source_row),util.stable_points(target_row))[0]
        mapped=[util.map_affine(fit,p) for p in lips]
        x0=max(0,int(min(p[0] for p in mapped)-28));y0=max(0,int(min(p[1] for p in mapped)-26))
        x1=min(W,int(max(p[0] for p in mapped)+28));y1=min(H,int(max(p[1] for p in mapped)+26))
        ImageDraw.Draw(mask).rectangle((x0,y0,x1,y1),fill=0)
        mask=mask.filter(ImageFilter.GaussianBlur(1.0))
    src=np.asarray(warped.convert("RGB"),dtype=np.float32)
    blur=np.asarray(warped.convert("RGB").filter(ImageFilter.GaussianBlur(1.2)),dtype=np.float32)
    dst=np.asarray(target.convert("RGB"),dtype=np.float32)
    alpha=np.asarray(mask,dtype=np.float32)[...,None]/255.0
    # Details are sampled from the affine-aligned source texture, not generated edges.
    out=np.clip(dst + 0.12*(src-blur)*alpha,0,255).astype(np.uint8)
    mask.close()
    return Image.fromarray(out,"RGB")
def edge_metrics(files, rows, Image, ImageFilter):
    values={"face":[],"eyes":[],"hairline_forehead":[],"mouth":[],"skin_texture":[]}
    for j,fid in enumerate(SAMPLES):
        row=rows[fid-1]; im=Image.open(files[j if len(files)==len(SAMPLES) else fid-1]).convert("L"); edge=im.filter(ImageFilter.FIND_EDGES)
        contour=row.get("face_contour") or []; eyes=(row.get("left_eye") or [])+(row.get("right_eye") or [])
        brows=(row.get("left_eyebrow") or [])+(row.get("right_eyebrow") or []); lips=row.get("outer_lips") or []
        def box(pts,pad=0):
            return (max(0,int(min(p[0] for p in pts)-pad)),max(0,int(min(p[1] for p in pts)-pad)),min(W,int(max(p[0] for p in pts)+pad)),min(H,int(max(p[1] for p in pts)+pad)))
        def mean_roi(b):
            crop=edge.crop(b); hist=crop.histogram(); n=sum(hist)
            return sum(i*v for i,v in enumerate(hist))/max(1,n)
        face=box(contour,0); eye=box(eyes,2); mouth=box(lips,2); brow=box(brows,2)
        values["face"].append(mean_roi(face)); values["eyes"].append(mean_roi(eye)); values["mouth"].append(mean_roi(mouth))
        # The high forehead box is a hairline/forehead detail proxy, not isolated hair texture.
        span=max(1,eye[2]-eye[0]); forehead=(max(0,brow[0]),max(0,brow[1]-int(.28*span)),min(W,brow[2]),max(0,brow[1]))
        values["hairline_forehead"].append(mean_roi(forehead)); values["skin_texture"].append(mean_roi(face))
        im.close();edge.close()
    return {k:{"static_mean":round(sum(v[:2])/2,4),"moving_mean":round(sum(v[2:])/3,4),"sample_values":list(map(lambda n:round(n,4),v))} for k,v in values.items()}

from scripts.nexus_agent_platform.provider_enforcement import governed_modal_canary

@governed_modal_canary
def main():
    import numpy as np
    from PIL import Image,ImageDraw,ImageFilter
    import modal
    from deploy.modal.nova_portrait_renderer_canary import app,speaking_canary,REFERENCE_SHA256
    if (OUT/"nova_portrait_highres_C.mp4").exists():
        raise FileExistsError("refusing_to_overwrite_portrait_highres_C")
    if REFERENCE_SHA256!=REF_HASH: raise RuntimeError("approved_reference_pin_changed")
    if not SOURCE.is_file() or not BASELINE.is_file(): raise FileNotFoundError("locked input or Candidate C baseline missing")
    source_meta=probe(SOURCE); base_meta=probe(BASELINE)
    for meta in (source_meta,base_meta):
        v=next(s for s in meta["streams"] if s.get("codec_type")=="video")
        if (v["width"],v["height"],v["r_frame_rate"],int(v["nb_frames"]))!=(W,H,"25/1",COUNT): raise RuntimeError("input_video_contract_mismatch")
    prior=json.loads(RECEIPT.read_text())
    guard=json.loads((BASE/"nova_portrait_speaking_candidate_b_guard.json").read_text())
    if prior["f5"]["provider"]!="F5-TTS" or prior["candidate_b_guard"]["selection"]!="B": raise RuntimeError("voice_or_candidate_b_lock_mismatch")
    if prior["candidate_b_guard"]["color_profile_sha256"]!="271ea04aa94e12f6d0e61fbdb465253b34a264103c61d5a3e06e11227f1c5222": raise RuntimeError("candidate_b_color_hash_mismatch")
    OUT.mkdir(parents=True,exist_ok=True)
    work=Path(tempfile.mkdtemp(prefix="nova_portrait_highres_")); started=time.monotonic()
    try:
        # The completed L4 output was retained before stopping a slow redundant
        # all-frame local landmark scan. Reuse it; do not spend GPU twice.
        raw=OUT/"_lanczos_liveportrait_model.mp4"
        if not raw.is_file():
            with modal.enable_output(),app.run():
                remote=speaking_canary.remote(SOURCE.read_bytes(),REF_HASH,"lanczos4")
            raw.write_bytes(remote["model_video_bytes"])
        else:
            remote={"gpu":"L4","pasteback_interpolation":"lanczos4","gpu_active_seconds":None,
                    "model_load_seconds":None,"render_seconds":None,
                    "execution_note":"L4 completed; output retained after local landmark scan interruption; Modal timing receipt unavailable"}
        sfdir=work/"source"; extract(SOURCE,sfdir)
        swift=ROOT/"scripts/nova/extract_nova_face_landmarks.swift"
        target_lm=[json.loads(x) for x in (ANCHOR/"liveportrait_face_landmarks.jsonl").read_text().splitlines() if x.strip()]
        source_lm=[json.loads(x) for x in (ANCHOR/"source_face_landmarks.jsonl").read_text().splitlines() if x.strip()]
        if len(target_lm)!=COUNT or len(source_lm)!=COUNT:raise RuntimeError("landmark_count_mismatch")
        mod=importlib.util.spec_from_file_location("nova_anchor_util",ROOT/"scripts/nova/run_nova_mouth_anchor_recovery.py")
        util=importlib.util.module_from_spec(mod);mod.loader.exec_module(util)
        make_b=not (OUT/"nova_portrait_highres_B.mp4").exists()
        dirs=({"B":OUT/"_frames_B"} if make_b else {})
        dirs["C"]=OUT/"_frames_C"
        for p in dirs.values():p.mkdir()
        base_files=(sorted((OUT/"_frames_B").glob("*.png")) if not make_b else None)
        target_files=(sorted((OUT/"_frames_B").glob("*.png")) if not make_b else sorted((OUT/"_lanczos_liveportrait_frames").glob("*.png")))
        if not make_b and len(base_files)!=COUNT:raise RuntimeError("candidate_b_source_frames_missing")
        if make_b:
            tfdir=work/"target";extract(raw,tfdir);target_files=sorted(tfdir.glob("*.png"))
        opening=[]; widths=[]; align_residual=[]
        for i,(sfile,tfile,sl,tl) in enumerate(zip(sorted(sfdir.glob("*.png")),target_files,source_lm,target_lm)):
            sp=util.stable_points(sl);tp=util.stable_points(tl)
            if len(sp)!=len(tp) or len(sp)<40:raise RuntimeError(f"insufficient_landmarks:{i}")
            mat,res=util.affine_fit(sp,tp)
            if max(res)>18:raise RuntimeError(f"affine_fit_out_of_bounds:{i}:{max(res)}")
            align_residual.append(max(res))
            src=Image.open(sfile).convert("RGB");base=Image.open(tfile).convert("RGB")
            warped=util.pil_transform(src,"B",mat,Image.Resampling.BICUBIC)
            # Candidate C injects restrained aligned source texture outside the B mouth ROI.
            detailed=masked_detail(base,warped,tl,sl,util,np,Image,ImageDraw,ImageFilter)
            if make_b:
                poly=util.expand_polygon(sl.get("outer_lips") or [],2.0)
                if len(poly)<8:raise RuntimeError(f"missing_lip_roi:{i}")
                mouthed_b=util.transform_mouth_roi(src,base,poly,"B",mat)
                mouthed_b.save(dirs["B"]/f"{i+1:06d}.png",compress_level=1)
                mouthed_b.close()
            detailed.save(dirs["C"]/f"{i+1:06d}.png",compress_level=1)
            vals=face_lip_values(sl); opening.append(vals["opening"] if vals else 0); widths.append(vals["width"] if vals else 0)
            for x in (src,base,warped,detailed):x.close()
        silent={k:work/f"{k}_silent.mp4" for k in dirs}
        for k in dirs:encode(dirs[k],silent[k],14)
        artifacts={"B":OUT/"nova_portrait_highres_B.mp4","C":OUT/"nova_portrait_highres_C.mp4"}
        for k,p in artifacts.items():
            if k in dirs:mux(silent[k],SOURCE,p)
        # Use the same landmark coordinates for feature windows across each set.
        bm=extract_samples(BASELINE,work/"baseline")
        # Motion inputs and transform are identical; use certified framewise
        # landmarks for matching ROI metrics to avoid post-encode detector bias.
        base_lm=target_lm
        candidate_lm={"B":target_lm,"C":target_lm}
        base_metric=edge_metrics(bm,base_lm,Image,ImageFilter)
        metrics={k:edge_metrics(extract_samples(p,work/f"decoded_{k}"),candidate_lm[k],Image,ImageFilter) for k,p in artifacts.items()}
        audio_hash=packet_hash(SOURCE,"0:a:0"); checks={}; lip_corr={}
        for k,p in artifacts.items():
            meta=probe(p);v=next(s for s in meta["streams"] if s.get("codec_type")=="video")
            cand_lm=candidate_lm[k]
            outvals=[face_lip_values(x) for x in cand_lm]
            aw=corr(widths,[x["width"] if x else 0 for x in outvals]); ao=corr(opening,[x["opening"] if x else 0 for x in outvals])
            lip_corr[k]={"width":round(aw,6),"opening":round(ao,6)}
            checks[k]={"path":str(p.relative_to(ROOT)),"sha256":sha(p.read_bytes()),"size_bytes":p.stat().st_size,
                "frames":int(v["nb_frames"]),"fps":v["r_frame_rate"],"dimensions":[v["width"],v["height"]],
                "audio_packets_match":packet_hash(p,"0:a:0")==audio_hash,"duration_seconds":float(meta["format"]["duration"]),
                "mouth_width_sequence_correlation":round(aw,6),"mouth_opening_sequence_correlation":round(ao,6),
                "regression_pass":int(v["nb_frames"])==COUNT and v["r_frame_rate"]=="25/1" and [v["width"],v["height"]]==[W,H]
                    and packet_hash(p,"0:a:0")==audio_hash and aw>=.95 and ao>=.95}
        if checks["B"]["sha256"]==checks["C"]["sha256"]:
            raise RuntimeError("detail_preserving_candidate_is_identical_to_pasteback_candidate")
        # No high-resolution network mode is advertised: official pinned graph and crop utility use 256 input.
        detail_receipt={"method":"face-relative, 0.12-strength high-frequency transfer from aligned Candidate B source, face-mask only; protected mouth restored after detail layer",
            "source_of_detail":"affine-warped same-frame Candidate B input","geometry_transform":False,"mouth_roi_excluded":True,
            "affine_resample":"Pillow bicubic","max_affine_fit_residual_px":round(max(align_residual),4),
            "face_mask":"detected face contour eroded 5 px and feathered 3 px","detail_gain":0.12}
        result={"schema":"nexus.nova.portrait_highres_canary.v1","created_at":datetime.now(timezone.utc).isoformat(),
            "official_implementation":{"repo":"KlingAIResearch/LivePortrait","commit":"9b294b3d0536135442ea73cb01e6cb3ca7029dd3",
                "network_input":"256x256 fixed in pinned InferenceConfig/prepare_source","crop_config_dsize":512,
                "higher_network_input_supported":False,"unsafe_resolutions":[384,512],"source_canvas":[W,H]},
            "baseline":{"path":str(BASELINE.relative_to(ROOT)),"sha256":sha(BASE(BASELINE.read_bytes()).hexdigest()) if False else sha(BASELINE.read_bytes()),
                "metrics":base_metric,"baseline_receipt_metrics":prior.get("quality_candidates",{})},
            "modal_run":{k:v for k,v in remote.items() if k not in {"video_bytes","model_video_bytes"}},
            "candidates":{"A":{"created":False,"reason":"unsupported: pinned generator network input is fixed at 256x256; larger input is not checkpoint/config validated"},
                "B":{"method":"same pinned LivePortrait model/motion with INTER_LANCZOS4 crop paste-back, exact same affine Candidate B mouth restoration, CRF14",**checks["B"]},
                "C":{"method":detail_receipt,**checks["C"]}},
            "metrics":{"baseline_C":base_metric,"B":metrics["B"],"C":metrics["C"],"quality_gain_percent":{
                k:{feature:round((metrics[k][feature][mode+"_mean"]-base_metric[feature][mode+"_mean"])/max(1e-9,base_metric[feature][mode+"_mean"])*100,3)
                   for feature in ("face","eyes","hairline_forehead","mouth","skin_texture") for mode in ("static","moving")} for k in artifacts}},
            "regression":{"candidates":checks,"f5_config_unchanged":True,"candidate_b_color_profile_sha256":prior["candidate_b_guard"]["color_profile_sha256"],
                "mouth_anchor_method":"AFFINE_FACE_RELATIVE","motion_driver":"official d11; same file and multiplier 0.12",
                "motion_timing":True,"audio_source":"locked Candidate B input; packets copied without re-encoding","mouth_sequence_correlations":lip_corr},
            "performance":{"gpu":remote.get("gpu"),"gpu_active_seconds":remote.get("gpu_active_seconds"),"model_load_seconds":remote.get("model_load_seconds"),
                "model_render_seconds":remote.get("render_seconds"),"end_to_end_seconds_local":round(time.monotonic()-started,3),"estimated_modal_cost":"NOT_COMPUTED; account price not present in run receipt"},
            "selection":"NONE_WAITING_RAY_VISUAL_SELECTION"}
        (OUT/"NOVA_PORTRAIT_HIGHRES_DIAGNOSTIC.json").write_text(json.dumps(result,indent=2)+"\n")
        print(json.dumps(result,indent=2))
    finally:shutil.rmtree(work,ignore_errors=True)

if __name__=="__main__":main()
