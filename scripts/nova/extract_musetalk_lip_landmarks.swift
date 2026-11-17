import AVFoundation
import CoreMedia
import CoreVideo
import Foundation
import ImageIO
import Vision

guard CommandLine.arguments.count == 2 else { fatalError("usage: extract_musetalk_lip_landmarks.swift input.mp4|png-directory") }
let url = URL(fileURLWithPath: CommandLine.arguments[1])
let request = VNDetectFaceLandmarksRequest()
request.revision = VNDetectFaceLandmarksRequestRevision3

func jsonLine(frame: Int, pts: Double, w: Int, h: Int, face: VNFaceObservation?) throws {
    var result: [String: Any] = ["frame": frame, "pts_seconds": pts]
    if let face = face {
        func points(_ region: VNFaceLandmarkRegion2D?) -> [[Double]] {
            guard let r = region else { return [] }
            return r.normalizedPoints.map { [Double((face.boundingBox.minX + $0.x * face.boundingBox.width) * CGFloat(w)), Double((1 - (face.boundingBox.minY + $0.y * face.boundingBox.height)) * CGFloat(h))] }
        }
        result["outer_lips"] = points(face.landmarks?.outerLips)
        result["inner_lips"] = points(face.landmarks?.innerLips)
    }
    let data = try JSONSerialization.data(withJSONObject: result, options: [.sortedKeys])
    print(String(data: data, encoding: .utf8)!)
}

if (try? url.resourceValues(forKeys: [.isDirectoryKey]).isDirectory) == true {
    let files = try FileManager.default.contentsOfDirectory(at: url, includingPropertiesForKeys: nil)
        .filter { $0.pathExtension.lowercased() == "png" }.sorted { $0.lastPathComponent < $1.lastPathComponent }
    for (index, file) in files.enumerated() {
        guard let source = CGImageSourceCreateWithURL(file as CFURL, nil),
              let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else { fatalError("PNG frame unreadable: \(file.lastPathComponent)") }
        try VNImageRequestHandler(cgImage: image, orientation: .up).perform([request])
        try jsonLine(frame: index, pts: Double(index) / 25.0, w: image.width, h: image.height, face: request.results?.first)
    }
} else {
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
        try jsonLine(frame: frame, pts: CMTimeGetSeconds(CMSampleBufferGetPresentationTimeStamp(sample)),
                     w: w, h: h, face: request.results?.first)
        frame += 1
    }
    if reader.status != .completed { fatalError("asset reader failed: \(reader.error?.localizedDescription ?? "unknown")") }
}
