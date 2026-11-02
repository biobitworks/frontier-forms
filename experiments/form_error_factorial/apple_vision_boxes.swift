import Foundation
import AppKit
import PDFKit
import Vision

// Native, on-device OCR with normalized boxes [x,y,width,height] in Vision's
// bottom-left origin. PDFKit text is a separate extraction arm.
guard CommandLine.arguments.count == 3 else {
  fputs("usage: swift apple_vision_boxes.swift form.pdf evidence.json\n",stderr)
  exit(2)
}
let src=URL(fileURLWithPath:CommandLine.arguments[1])
let dest=URL(fileURLWithPath:CommandLine.arguments[2])
guard let pdf=PDFDocument(url:src) else {fatalError("Cannot load synthetic PDF")}
var pages=[[String:Any]]()
for i in 0..<pdf.pageCount {
 guard let page=pdf.page(at:i) else {continue}
 let size=NSSize(width:1530,height:1980)
 let img=page.thumbnail(of:size,for:.mediaBox)
 var rect=NSRect(origin:.zero,size:img.size)
 guard let cg=img.cgImage(forProposedRect:&rect,context:nil,hints:nil)
 else {fatalError("Raster render failed")}
 let request=VNRecognizeTextRequest()
 request.recognitionLevel = .accurate
 request.usesLanguageCorrection = false
 request.recognitionLanguages = ["en-US"]
 try VNImageRequestHandler(cgImage:cg,options:[:]).perform([request])
 let lines:[[String:Any]]=(request.results ?? []).compactMap { o in
   guard let candidate=o.topCandidates(1).first else {return nil}
   let box=o.boundingBox
   return [
    "text":candidate.string,
    "confidence":Double(candidate.confidence),
    "bbox_norm_bl":[Double(box.origin.x), Double(box.origin.y),
                    Double(box.width), Double(box.height)]
   ]
 }
 pages.append(["page_index":i,"pixel_width":cg.width,"pixel_height":cg.height,"lines":lines])
}
let out:[String:Any]=["engine":"Apple Vision VNRecognizeTextRequest",
 "engine_version":"OS-native",
 "bbox_format":"normalized bottom-left x,y,width,height",
 "pages":pages,"pdfkit_text":pdf.string ?? "",
 "pdfkit_text_is_not_ocr":true]
let bytes=try JSONSerialization.data(withJSONObject:out,options:[.sortedKeys,.prettyPrinted])
try bytes.write(to:dest,options:.atomic)
print("APPLE_VISION_BOXES pages=\(pages.count) lines=\(pages.reduce(0){$0 + (($1["lines"] as? [[String:Any]])?.count ?? 0)})")
