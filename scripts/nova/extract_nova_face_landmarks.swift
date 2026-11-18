import AVFoundation
import CoreMedia
import CoreVideo
import Foundation
import Vision

guard CommandLine.arguments.count == 2 else { fatalError("usage: extract_nova_face_landmarks.swift video.mp4") }
let url = URL(fileURLWithPath: CommandLine.arguments[1])
let request = VNDetectFaceLandmarksRequest()
request.revision = VNDetectFaceLandmarksRequestRevision3

func emit(frame: Int, pts: Double, w: Int, h: Int, face: VNFaceObservation?) throws {
    var result: [String: Any] = ["frame": frame, "pts_seconds": pts, "width": w, "height": h]
    if let face = face {
        result["face_box"] = [Double(face.boundingBox.minX * CGFloat(w)), Double((1-face.boundingBox.maxY) * CGFloat(h)), Double(face.boundingBox.width * CGFloat(w)), Double(face.boundingBox.height * CGFloat(h))]
        func points(_ region: VNFaceLandmarkRegion2D?) -> [[Double]] {
            guard let r = region else { return [] }
            return r.normalizedPoints.map { [Double((face.boundingBox.minX + $0.x * face.boundingBox.width) * CGFloat(w)), Double((1 - (face.boundingBox.minY + $0.y * face.boundingBox.height)) * CGFloat(h))] }
        }
        result["left_eye"] = points(face.landmarks?.leftEye)
        result["right_eye"] = points(face.landmarks?.rightEye)
        result["left_eyebrow"] = points(face.landmarks?.leftEyebrow)
        result["right_eyebrow"] = points(face.landmarks?.rightEyebrow)
        result["nose"] = points(face.landmarks?.nose)
        result["nose_crest"] = points(face.landmarks?.noseCrest)
        result["face_contour"] = points(face.landmarks?.faceContour)
        result["outer_lips"] = points(face.landmarks?.outerLips)
        result["inner_lips"] = points(face.landmarks?.innerLips)
    }
    let data = try JSONSerialization.data(withJSONObject: result, options: [.sortedKeys])
    print(String(data: data, encoding: .utf8)!)
}
let asset = AVURLAsset(url: url)
guard let track = asset.tracks(withMediaType: .video).first else { fatalError("video track missing") }
let reader = try AVAssetReader(asset: asset)
let settings: [String: Any] = [kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA]
let output = AVAssetReaderTrackOutput(track: track, outputSettings: settings)
output.alwaysCopiesSampleData = false
guard reader.canAdd(output) else { fatalError("cannot add video output") }
reader.add(output)
guard reader.startReading() else { fatalError("reader failed to start") }
var frame = 0
while let sample = output.copyNextSampleBuffer() {
    guard let pixel = CMSampleBufferGetImageBuffer(sample) else { fatalError("pixel buffer missing") }
    let w = CVPixelBufferGetWidth(pixel), h = CVPixelBufferGetHeight(pixel)
    try VNImageRequestHandler(cvPixelBuffer: pixel, orientation: .up).perform([request])
    try emit(frame: frame, pts: CMTimeGetSeconds(CMSampleBufferGetPresentationTimeStamp(sample)), w: w, h: h, face: request.results?.first)
    frame += 1
}
if reader.status != .completed { fatalError("asset reader failed: \(reader.error?.localizedDescription ?? "unknown")") }
