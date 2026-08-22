import AVFoundation
import ImageIO
import CoreVideo
import CoreGraphics
import Foundation

let args = CommandLine.arguments
guard args.count == 3 else { exit(2) }
let frameDir = URL(fileURLWithPath: args[1])
let output = URL(fileURLWithPath: args[2])
try? FileManager.default.removeItem(at: output)
let writer = try AVAssetWriter(outputURL: output, fileType: .mp4)
let settings: [String: Any] = [AVVideoCodecKey: AVVideoCodecType.h264, AVVideoWidthKey: 1080, AVVideoHeightKey: 1080, AVVideoCompressionPropertiesKey: [AVVideoAverageBitRateKey: 1_500_000]]
let input = AVAssetWriterInput(mediaType: .video, outputSettings: settings)
input.expectsMediaDataInRealTime = false
let adaptor = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: input, sourcePixelBufferAttributes: [kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32ARGB, kCVPixelBufferWidthKey as String: 1080, kCVPixelBufferHeightKey as String: 1080])
writer.add(input); writer.startWriting(); writer.startSession(atSourceTime: .zero)
let frames = [0, 60, 120, 180, 239]
for (index, frame) in frames.enumerated() {
    let url = frameDir.appendingPathComponent("frame-\(frame).png")
    guard let source = CGImageSourceCreateWithURL(url as CFURL, nil), let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else { exit(3) }
    var buffer: CVPixelBuffer?
    CVPixelBufferCreate(kCFAllocatorDefault, 1080, 1080, kCVPixelFormatType_32ARGB, nil, &buffer)
    guard let pixel = buffer else { exit(4) }
    CVPixelBufferLockBaseAddress(pixel, [])
    let context = CGContext(data: CVPixelBufferGetBaseAddress(pixel), width: 1080, height: 1080, bitsPerComponent: 8, bytesPerRow: CVPixelBufferGetBytesPerRow(pixel), space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.noneSkipFirst.rawValue)
    context?.draw(image, in: CGRect(x: 0, y: 0, width: 1080, height: 1080)); CVPixelBufferUnlockBaseAddress(pixel, [])
    let repeatCount = index == frames.count - 1 ? 1 : 48
    for repeatIndex in 0..<repeatCount {
        while !input.isReadyForMoreMediaData { Thread.sleep(forTimeInterval: 0.01) }
        adaptor.append(pixel, withPresentationTime: CMTime(value: CMTimeValue(index * 48 + repeatIndex), timescale: 30))
    }
}
input.markAsFinished(); let semaphore = DispatchSemaphore(value: 0); writer.finishWriting { semaphore.signal() }; semaphore.wait(); if writer.status != .completed { exit(5) }
