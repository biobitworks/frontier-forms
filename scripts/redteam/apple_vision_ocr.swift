// Apple Vision OCR (the on-device text recognizer behind Preview/Live Text), batch mode, no AppKit (headless-safe).
// First call pays a ~35 s model warm-up on magicSTUDIObox; later images take well under a second.
// Usage: swift apple_vision_ocr.swift <image paths...>  -> JSON array on stdout
// [{"path":..., "lines":[{"text":..., "confidence":..., "x":..., "y":..., "w":..., "h":...}], "error": null}]
// Bounding boxes are Vision-normalized (origin bottom-left, 0..1). No network, no model download.
import Foundation
import Vision
import ImageIO
import CoreGraphics

var results: [[String: Any]] = []
for path in CommandLine.arguments.dropFirst() {
    var entry: [String: Any] = ["path": path, "lines": [], "error": NSNull()]
    let url = URL(fileURLWithPath: path)
    guard let src = CGImageSourceCreateWithURL(url as CFURL, nil),
          let cg = CGImageSourceCreateImageAtIndex(src, 0, nil) else {
        entry["error"] = "IMAGE_LOAD_FAILED"; results.append(entry); continue
    }
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.usesLanguageCorrection = false
    req.recognitionLanguages = ["en-US"]
    let t0 = Date()
    do {
        try VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
        var lines: [[String: Any]] = []
        for obs in req.results ?? [] {
            guard let c = obs.topCandidates(1).first else { continue }
            lines.append(["text": c.string, "confidence": Double(c.confidence),
                          "x": Double(obs.boundingBox.minX), "y": Double(obs.boundingBox.minY),
                          "w": Double(obs.boundingBox.width), "h": Double(obs.boundingBox.height)])
        }
        entry["lines"] = lines
        entry["seconds"] = Date().timeIntervalSince(t0)
    } catch {
        entry["error"] = "VISION_ERROR: \(error)"
    }
    results.append(entry)
}
let data = try JSONSerialization.data(withJSONObject: results, options: [.sortedKeys])
FileHandle.standardOutput.write(data)
FileHandle.standardOutput.write("\n".data(using: .utf8)!)
