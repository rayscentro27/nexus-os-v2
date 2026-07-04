import Foundation
import CoreImage
import AppKit
let value = ProcessInfo.processInfo.environment["GOCLEAR_QR_URL"] ?? "https://goclearonline.cc/got-funding/"
let output = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "public/got-funding/qr-got-funding.png"
guard let filter=CIFilter(name:"CIQRCodeGenerator") else { fatalError("QR filter unavailable") }
filter.setValue(Data(value.utf8),forKey:"inputMessage"); filter.setValue("M",forKey:"inputCorrectionLevel")
guard let image=filter.outputImage?.transformed(by:CGAffineTransform(scaleX:12,y:12)) else { fatalError("QR generation failed") }
let rep=NSCIImageRep(ciImage:image); let ns=NSImage(size:rep.size); ns.addRepresentation(rep)
guard let tiff=ns.tiffRepresentation,let bitmap=NSBitmapImageRep(data:tiff),let png=bitmap.representation(using:.png,properties:[:]) else { fatalError("PNG encoding failed") }
try png.write(to:URL(fileURLWithPath:output))
let svg=output.replacingOccurrences(of:".png",with:".svg")
let payload=png.base64EncodedString()
let xml="<svg xmlns=\"http://www.w3.org/2000/svg\" xmlns:xlink=\"http://www.w3.org/1999/xlink\" viewBox=\"0 0 \(Int(rep.size.width)) \(Int(rep.size.height))\" role=\"img\" aria-label=\"QR code to \(value)\"><title>GoClear Got Funding QR — \(value)</title><a href=\"\(value)\"><image width=\"100%\" height=\"100%\" image-rendering=\"pixelated\" xlink:href=\"data:image/png;base64,\(payload)\"/></a></svg>"
try xml.data(using:.utf8)!.write(to:URL(fileURLWithPath:svg))
print("Generated QR for \(value) at \(output) and \(svg)")
