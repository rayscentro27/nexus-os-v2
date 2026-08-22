import React from "react";
import {AbsoluteFill, Composition, Sequence, interpolate, registerRoot, useCurrentFrame} from "remotion";

const DEFAULT_SCENES = [
  {name: "HOOK", seconds: 1.5, text: "Funding readiness starts before you apply."},
  {name: "PROBLEM", seconds: 1.5, text: "Know what to prepare first."},
  {name: "READINESS", seconds: 3, text: "Profile  •  Documents  •  Credit readiness"},
  {name: "CTA", seconds: 1, text: "Review your readiness"},
  {name: "DISCLAIMER", seconds: 1, text: "Education and readiness only. No guaranteed funding or approval."},
];

function Scene({text, name, durationInFrames, frame}) {
  const opacity = interpolate(frame, [0, 12, durationInFrames - 12, durationInFrames], [0, 1, 1, 0], {extrapolateLeft: "clamp", extrapolateRight: "clamp"});
  const scale = interpolate(frame, [0, durationInFrames], [0.96, 1], {extrapolateLeft: "clamp", extrapolateRight: "clamp"});
  return <AbsoluteFill style={{opacity, transform: `scale(${scale})`, justifyContent: "center", alignItems: "center", padding: 90}}>
    <div style={{position: "absolute", top: 80, left: 90, color: "#c7a45a", fontFamily: "Arial", fontSize: 26, letterSpacing: 4}}>{name}</div>
    <div style={{color: "#f8f4ea", fontFamily: "Arial", fontWeight: 700, fontSize: name === "DISCLAIMER" ? 27 : 64, lineHeight: 1.1, textAlign: "center", maxWidth: 880}}>{text}</div>
  </AbsoluteFill>;
}

function Video({scenes = DEFAULT_SCENES}) {
  const frame = useCurrentFrame();
  let offset = 0;
  const rendered = scenes.map((scene) => {
    const durationInFrames = Math.max(1, Math.round(Number(scene.seconds) * 30));
    const start = offset; offset += durationInFrames;
    return <Sequence key={`${scene.name}-${start}`} from={start} durationInFrames={durationInFrames}><Scene {...scene} durationInFrames={durationInFrames} frame={frame - start} /></Sequence>;
  });
  return <AbsoluteFill style={{background: "linear-gradient(145deg, #071a2b 0%, #123b52 55%, #0b2336 100%)"}}>{rendered}<div style={{position: "absolute", bottom: 45, right: 70, width: 140, height: 8, background: "#c7a45a", borderRadius: 4}} /></AbsoluteFill>;
}

export const RemotionRoot = () => <Composition id="goclear-readiness-explainer" component={Video} durationInFrames={240} fps={30} width={1080} height={1080} defaultProps={{scenes: DEFAULT_SCENES}} />;
registerRoot(RemotionRoot);
