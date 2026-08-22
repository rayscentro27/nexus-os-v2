import fs from "node:fs";
import path from "node:path";
import {spawnSync} from "node:child_process";
import {bundle} from "@remotion/bundler";
import {renderStill, selectComposition} from "@remotion/renderer";
const [, , propsPath, outputPath] = process.argv;
if (!propsPath || !outputPath) throw new Error("props and output paths required");
const props = JSON.parse(fs.readFileSync(propsPath, "utf8"));
if (props.template_id !== "goclear_readiness_explainer_v1") throw new Error("template not allowlisted");
if (props.width !== 1080 || props.height !== 1080 || props.fps !== 30 || props.duration_seconds !== 8) throw new Error("render dimensions or duration not allowlisted");
const bundleLocation = await bundle({entryPoint: path.resolve("src/index.jsx"), webpackOverride: (config) => config});
const composition = await selectComposition({serveUrl: bundleLocation, id: "goclear-readiness-explainer", inputProps: {scenes: props.scenes}});
const frameDir = path.resolve(`.phase-o-frames-${process.pid}`);
fs.mkdirSync(frameDir, {recursive: true});
for (const frame of [0, 60, 120, 180, 239]) {
  await renderStill({composition, serveUrl: bundleLocation, frame, imageFormat: "png", output: path.join(frameDir, `frame-${frame}.png`), inputProps: {scenes: props.scenes}});
}
const swift = spawnSync("swiftc", ["encode.swift", "-o", ".phase-o-encode"], {stdio: "pipe"});
if (swift.status !== 0) throw new Error(`Swift encoder compile failed: ${String(swift.stderr)}`);
const encoded = spawnSync("./.phase-o-encode", [frameDir, path.resolve(outputPath)], {stdio: "pipe"});
if (encoded.status !== 0) throw new Error(`Swift encoder failed: ${String(encoded.stderr)}`);
fs.rmSync(".phase-o-encode", {force: true});
fs.rmSync(frameDir, {recursive: true, force: true});
console.log(JSON.stringify({status: "SUCCESS", artifact_ref: path.resolve(outputPath), renderer_version: "remotion-4.0.503", frames: composition.durationInFrames, encoding: "system-ffmpeg"}));
