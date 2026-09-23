# Nexus Consistent Avatar System Research

## Requirement

`CONSISTENT_AVATAR_SYSTEM=REQUIRED`

Nexus needs a reusable identity that can appear across short-form video, image ads, landing pages, social posts, explainers, and future voice/avatar interactions without silently becoming a new person each campaign.

## Feasible approaches

### 1. Reference-image identity system

Use a canonical reference sheet with neutral front, profile, three-quarter, full-body, expression, and wardrobe views. Hosted reference systems such as Runway Gen-4 References document reusable single/multi-image character references across lighting, locations, and treatments. This is the lowest-friction high-quality option, but it is paid and proprietary. [Runway References](https://help.runwayml.com/hc/en-us/articles/40042718905875-Creating-with-Gen-4-Image-References)

### 2. Open image identity pipeline

Use ComfyUI plus IP-Adapter/InstantID-style conditioning for image references, then pass approved keyframes into a video workflow. This is self-hostable and gives Nexus control, but requires GPU operations, model/checkpoint licensing, workflow maintenance, and identity QA. [ComfyUI](https://github.com/Comfy-Org/ComfyUI), [IP-Adapter](https://arxiv.org/abs/2308.06721), [InstantID nodes](https://github.com/cubiq/ComfyUI_InstantID)

### 3. Stylized/illustrated recurring character

A mascot, illustrated person, or recurring stylized figure can be more robust than photoreal identity across image/video/web. It reduces biometric likeness and voice-consent risk, while preserving a recognizable campaign signal. It still requires a reference sheet and drift checks. This is a Creative decision, not a system default.

### 4. Talking-avatar system

For presenter-led explainers, HeyGen Avatar V and open-source LivePortrait/HunyuanVideo-Avatar-like systems provide audio/face animation options. HeyGen is commercially practical but paid; LivePortrait is a research/open route requiring an additional voice and compositing stack; Hunyuan’s license requires review. [HeyGen Avatar V report](https://dynamic.heygen.ai/www/Paper%20Links/avatarv_tech_report.pdf), [LivePortrait](https://github.com/KwaiVGI/LivePortrait), [Hunyuan license](https://github.com/Tencent-Hunyuan/HunyuanVideo-Avatar/blob/main/LICENSE)

### 5. Voice identity

Use a versioned `VOICE_ID` and consent receipt. ElevenLabs documents voice-clone API creation, but the contract must require consent and commercial-use authorization before any real-person voice is used. [ElevenLabs voice API](https://elevenlabs.io/docs/api-reference/voices/ivc/create)

## Recommended identity contract

```json
{
  "avatar_id": "avatar_<stable_id>",
  "avatar_name": "<creative-owned name>",
  "brand": "GoClear",
  "role": "<creative-owned role>",
  "style": "<photoreal | illustrated | mascot | stylized human>",
  "reference_images": [
    {"id": "ref_front_v1", "path_or_uri": "", "sha256": ""},
    {"id": "ref_profile_v1", "path_or_uri": "", "sha256": ""},
    {"id": "ref_three_quarter_v1", "path_or_uri": "", "sha256": ""},
    {"id": "ref_full_body_v1", "path_or_uri": "", "sha256": ""}
  ],
  "reference_video": {"path_or_uri": "", "sha256": ""},
  "face_identity_reference": {"path_or_uri": "", "sha256": ""},
  "body_reference": {"path_or_uri": "", "sha256": ""},
  "voice_id": null,
  "voice_style": null,
  "consent_receipt": null,
  "wardrobe_guidance": null,
  "color_palette": null,
  "personality": null,
  "gesture_style": null,
  "camera_guidance": null,
  "prohibited_changes": [
    "silent facial identity change",
    "silent age-range change",
    "silent voice identity change",
    "unversioned role/name change"
  ],
  "version": 1,
  "created_at": null,
  "lineage": []
}
```

## Identity governance

- `AVATAR_VERSION_INCREMENT_REQUIRED=YES` for material facial, age-range, voice, role, or name changes.
- Creative may vary clothing, environment, camera, action, mood, pose, lighting, and supported style while preserving identity.
- Every asset stores `AVATAR_ID`, `AVATAR_VERSION`, reference hashes, provider, prompt/input receipt, and drift result.
- A visual QA pass compares face/shape/voice identity to the canonical references; “same prompt” is not evidence of persistence.
- Real-person avatars and voices require explicit consent and commercial-use evidence. A fully synthetic/stylized character is the safer first canary.
- Do not use Tencent InstantCharacter for commercial production; its published license is research/education only. [License](https://github.com/Tencent-Hunyuan/InstantCharacter/blob/main/License.txt)

## Avatar option assessment

| Option | Identity persistence | Voice | Cost | Main risk | Status |
|---|---|---|---|---|---|
| Synthetic stylized character + reference sheet | High when style is constrained | Separate voice lane | Low | Creative may dislike reduced realism | LAB_TEST |
| ComfyUI + IP-Adapter/InstantID + keyframes | Medium–high for images; video requires QA | Separate LivePortrait/TTS lane | Low after GPU setup | GPU, workflow, checkpoint licenses | LAB_TEST |
| Runway Gen-4 References | High documented image/video potential | Separate voice/avatar product | Paid | Vendor lock-in and cost | LAB_TEST |
| HeyGen Avatar V | High for presenter workflow | Built-in/associated voice path | Paid | Presenter format can narrow Creative | LAB_TEST |
| LivePortrait + consented TTS | Medium for talking portraits | External TTS | Low/self-hosted | Narrow shot range and compositing | LAB_TEST |
| InstantCharacter | Technically promising | No complete voice lane | Free/research | Commercial prohibition | REJECT_PRODUCTION |

## Recommendation

Start with a synthetic stylized or illustrated identity canary, not a real person. Test one canonical reference sheet across one still, one short video, one web placement, and one voice-free social frame. Only then compare a photoreal hosted reference system or talking-avatar provider.
