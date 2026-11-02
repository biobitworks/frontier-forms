// Apple-native form front end for the Frontier Forms comparison arm.
//
// Uses only frameworks shipped with macOS: PDFKit (the engine behind
// Preview's form filling) and Vision (Apple's on-device OCR, as in Live Text).
// No network, no hosted models.
//
//   AppleForms make-pdf  <template.json> <out.pdf>       frozen fillable PDF form
//   AppleForms inspect   <form.pdf>                      widgets + OCR'd labels (JSON)
//   AppleForms fill      <form.pdf> <values.json> <out>  fill widgets like Preview does
//   AppleForms readback  <filled.pdf>                    OCR text inside each widget (JSON)
//
// Build: swiftc -O tools/apple_forms/AppleForms.swift -o AppleForms
import AppKit
import Foundation
import PDFKit
import Vision

let pageRect = CGRect(x: 0, y: 0, width: 612, height: 792)
let renderScale: CGFloat = 3.0

func die(_ msg: String) -> Never {
    FileHandle.standardError.write((msg + "\n").data(using: .utf8)!)
    exit(2)
}

func emit(_ obj: Any) {
    let data = try! JSONSerialization.data(withJSONObject: obj, options: [.sortedKeys, .prettyPrinted])
    FileHandle.standardOutput.write(data)
    FileHandle.standardOutput.write("\n".data(using: .utf8)!)
}

// MARK: make-pdf

func makePDF(templatePath: String, outPath: String) {
    guard let data = FileManager.default.contents(atPath: templatePath),
          let t = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
          let fields = t["fields"] as? [[String: Any]] else { die("bad template") }
    // Draw static text (title, banner, labels) into a PDF page.
    let pdfData = NSMutableData()
    var box = pageRect
    guard let consumer = CGDataConsumer(data: pdfData as CFMutableData),
          let ctx = CGContext(consumer: consumer, mediaBox: &box, nil) else { die("ctx") }
    ctx.beginPDFPage(nil)
    let ns = NSGraphicsContext(cgContext: ctx, flipped: false)
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = ns
    func draw(_ s: String, _ y: CGFloat, size: CGFloat, bold: Bool = false) {
        let font = bold ? NSFont.boldSystemFont(ofSize: size) : NSFont.systemFont(ofSize: size)
        (s as NSString).draw(at: CGPoint(x: 48, y: y), withAttributes: [.font: font, .foregroundColor: NSColor.black])
    }
    var y: CGFloat = 744
    draw("SYNTHETIC DEMO FORM. Not a real clinic.", y, size: 9)
    y -= 24
    draw(t["title"] as? String ?? "", y, size: 14, bold: true)
    y -= 22
    if let notice = t["untrusted_notice"] as? String {
        draw(notice, y, size: 9)
        y -= 18
    }
    var widgets: [(String, CGRect, [String]?, Bool)] = []
    for f in fields {
        let key = f["field_key"] as! String
        let label = f["label"] as! String
        let type = f["type"] as! String
        y -= 16
        draw(label, y, size: 11)
        let h: CGFloat = type == "textarea" ? 54 : 20
        y -= (h + 4)
        let rect = CGRect(x: 48, y: y, width: 516, height: h)
        widgets.append((key, rect, f["options"] as? [String], type == "textarea"))
        y -= 6
    }
    NSGraphicsContext.restoreGraphicsState()
    ctx.endPDFPage()
    ctx.closePDF()
    guard let doc = PDFDocument(data: pdfData as Data), let page = doc.page(at: 0) else { die("pdf") }
    for (key, rect, options, multi) in widgets {
        let w = PDFAnnotation(bounds: rect, forType: .widget, withProperties: nil)
        w.fieldName = key
        let border = PDFBorder()
        border.lineWidth = 0.75
        w.border = border
        w.color = NSColor.gray
        w.backgroundColor = NSColor.white
        if let options = options {
            w.widgetFieldType = .choice
            w.isListChoice = false
            w.choices = options
            w.font = NSFont.systemFont(ofSize: 10)
        } else {
            w.widgetFieldType = .text
            w.isMultiline = multi
            w.font = NSFont.systemFont(ofSize: multi ? 8 : 10)
        }
        page.addAnnotation(w)
    }
    guard doc.write(toFile: outPath) else { die("write failed") }
}

// MARK: rendering + OCR

func render(_ page: PDFPage) -> CGImage {
    let w = Int(pageRect.width * renderScale), h = Int(pageRect.height * renderScale)
    let cs = CGColorSpaceCreateDeviceRGB()
    let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: 0, space: cs,
                        bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
    ctx.setFillColor(NSColor.white.cgColor)
    ctx.fill(CGRect(x: 0, y: 0, width: w, height: h))
    ctx.scaleBy(x: renderScale, y: renderScale)
    page.draw(with: .mediaBox, to: ctx)
    return ctx.makeImage()!
}

struct Line { let text: String; let rect: CGRect; let confidence: Float }

func ocr(_ image: CGImage, region: CGRect? = nil) -> [Line] {
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.usesLanguageCorrection = false
    req.recognitionLanguages = ["en-US"]
    if let r = region {
        req.regionOfInterest = CGRect(x: r.minX / pageRect.width, y: r.minY / pageRect.height,
                                      width: r.width / pageRect.width, height: r.height / pageRect.height)
    }
    try! VNImageRequestHandler(cgImage: image, options: [:]).perform([req])
    var out: [Line] = []
    for obs in req.results ?? [] {
        guard let cand = obs.topCandidates(1).first else { continue }
        var b = obs.boundingBox  // normalised, relative to ROI when set
        if let r = region {
            b = CGRect(x: r.minX + b.minX * r.width, y: r.minY + b.minY * r.height,
                       width: b.width * r.width, height: b.height * r.height)
        } else {
            b = CGRect(x: b.minX * pageRect.width, y: b.minY * pageRect.height,
                       width: b.width * pageRect.width, height: b.height * pageRect.height)
        }
        out.append(Line(text: cand.string, rect: b, confidence: cand.confidence))
    }
    return out.sorted { ($0.rect.maxY, -$0.rect.minX) > ($1.rect.maxY, -$1.rect.minX) }
}

func widgetsOf(_ page: PDFPage) -> [PDFAnnotation] {
    page.annotations.filter { $0.type == "Widget" && $0.fieldName != nil }
        .sorted { $0.bounds.maxY > $1.bounds.maxY }
}

// MARK: inspect

func inspect(_ path: String) {
    guard let doc = PDFDocument(url: URL(fileURLWithPath: path)), let page = doc.page(at: 0) else { die("open") }
    // OCR the page with widgets hidden so only printed text is read, as a scan would show.
    let ws = widgetsOf(page)
    for w in ws { w.shouldDisplay = false }
    let lines = ocr(render(page))
    for w in ws { w.shouldDisplay = true }
    var fields: [[String: Any]] = []
    for w in ws {
        // label = nearest OCR line whose bottom sits within 22pt above the widget top
        let cands = lines.filter { $0.rect.minY >= w.bounds.maxY - 2 && $0.rect.minY <= w.bounds.maxY + 22 }
        let best = cands.min { abs($0.rect.minY - w.bounds.maxY) < abs($1.rect.minY - w.bounds.maxY) }
        var f: [String: Any] = [
            "name": w.fieldName!,
            "label": best?.text ?? "",
            "label_confidence": best.map { Double($0.confidence) } ?? 0.0,
            "rect": [w.bounds.minX, w.bounds.minY, w.bounds.width, w.bounds.height],
            "type": w.widgetFieldType == .choice ? "select" : (w.isMultiline ? "textarea" : "text"),
        ]
        if w.widgetFieldType == .choice { f["options"] = w.choices ?? [] }
        fields.append(f)
    }
    emit(["fields": fields, "ocr_lines": lines.map { ["text": $0.text, "y": $0.rect.minY] }])
}

// MARK: fill

func fill(_ path: String, valuesPath: String, outPath: String) {
    guard let doc = PDFDocument(url: URL(fileURLWithPath: path)), let page = doc.page(at: 0),
          let data = FileManager.default.contents(atPath: valuesPath),
          let values = try? JSONSerialization.jsonObject(with: data) as? [String: String] else { die("fill input") }
    for w in widgetsOf(page) {
        if let v = values[w.fieldName!] { w.widgetStringValue = v }
    }
    guard doc.write(toFile: outPath) else { die("write failed") }
}

// MARK: readback

func readback(_ path: String) {
    guard let doc = PDFDocument(url: URL(fileURLWithPath: path)), let page = doc.page(at: 0) else { die("open") }
    let img = render(page)
    var out: [String: Any] = [:]
    for w in widgetsOf(page) {
        let lines = ocr(img, region: w.bounds.insetBy(dx: 1, dy: 1))
        out[w.fieldName!] = [
            "text": lines.map { $0.text }.joined(separator: " "),
            "min_confidence": lines.map { Double($0.confidence) }.min() ?? 1.0,
            "pdf_value": w.widgetStringValue ?? "",
        ]
    }
    emit(out)
}

let a = CommandLine.arguments
guard a.count >= 3 else { die("usage: AppleForms make-pdf|inspect|fill|readback ...") }
switch a[1] {
case "make-pdf": makePDF(templatePath: a[2], outPath: a[3])
case "inspect": inspect(a[2])
case "fill": fill(a[2], valuesPath: a[3], outPath: a[4])
case "readback": readback(a[2])
default: die("unknown command")
}
