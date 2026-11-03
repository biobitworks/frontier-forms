#!/usr/bin/env python3
"""V2: train a local field-box detector (YOLOv8n) on rendered synthetic forms, then use it as a validator.

Input: a render directory produced by tools/render/render_forms.js from
scripts/build_detector_jobs.py jobs (PNG + GOLD_BOXES.json). Images and weights stay
LOCAL; this script writes only JSON/JSONL evidence to --out.

Detector: classes input / textarea / select, trained on train-split patients (seen
templates), early-stopped on validation-split patients. Evaluated on test-split
patients, separately for seen templates and the held-out layout (urgent_care_history_v1).

Validator: detected boxes are assigned to the form's fields in reading order (abstain if
the box count differs from the field count). Each crop is OCR'd with local Tesseract and
compared with the value the filler PLANNED to write:
  PASS          OCR text == planned value
  FLAG          they differ (written value is wrong, missing or unreadable)
  UNVERIFIABLE  text area whose visible text is a prefix of a longer planned value (clipped)
Truth for a field = the DOM value actually written differs from the plan.

    python3 scripts/train_forms_detector.py --render runs/detector_render_v1 --work runs/detector_v1 \
        --out evidence/forms_detector/V2-yolov8n
"""
import argparse
import csv
import hashlib
import json
import platform
import random
import re
import shutil
import subprocess
import time
from pathlib import Path

CLASSES = ["input", "textarea", "select"]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", str(s or "").lower()).strip()


def iou(a, b):
    x1, y1, x2, y2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def held_out(g):
    return bool((g.get("perturbation") or {}).get("held_out_layout"))


def build_dataset(render, gold, work):
    from PIL import Image
    ds = work / "yolo"
    if ds.exists():
        shutil.rmtree(ds)
    for img_id, g in gold.items():
        split = {"train": "train", "validation": "val", "test": "test_heldout" if held_out(g) else "test_seen"}[g["split"]]
        (ds / "images" / split).mkdir(parents=True, exist_ok=True)
        (ds / "labels" / split).mkdir(parents=True, exist_ok=True)
        src = render / g["image"]
        shutil.copy(src, ds / "images" / split / g["image"])
        W, H = Image.open(src).size
        lines = []
        for f in g["fields"]:
            x1, y1, x2, y2 = f["bbox"]
            lines.append(f"{CLASSES.index(f['tag'])} {(x1 + x2) / 2 / W:.6f} {(y1 + y2) / 2 / H:.6f} {(x2 - x1) / W:.6f} {(y2 - y1) / H:.6f}")
        (ds / "labels" / split / (Path(g["image"]).stem + ".txt")).write_text("\n".join(lines) + "\n")
    yamls = {}
    for name, val in (("train", "val"), ("test_seen", "test_seen"), ("test_heldout", "test_heldout")):
        y = ds / f"{name}.yaml"
        y.write_text(f"path: {ds}\ntrain: images/train\nval: images/{val}\nnames:\n" + "".join(f"  {i}: {c}\n" for i, c in enumerate(CLASSES)))
        yamls[name] = y
    return ds, yamls


def ocr(crop_path, textarea):
    r = subprocess.run(["tesseract", str(crop_path), "-", "--psm", "6" if textarea else "7"],
                       capture_output=True, text=True, timeout=60)
    return " ".join(r.stdout.split())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", required=True)
    ap.add_argument("--jobs", default=None, help="job list used for rendering (hash recorded)")
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--base", default="yolov8n.pt")
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--imgsz", type=int, default=960)
    ap.add_argument("--device", default="mps")
    ap.add_argument("--seed", type=int, default=20261102)
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--reuse-run", default=None,
                    help="existing ultralytics run dir (with weights/best.pt, results.csv): skip training, evaluate only")
    a = ap.parse_args()
    import torch
    import ultralytics
    from PIL import Image
    from ultralytics import YOLO

    random.seed(a.seed)
    torch.manual_seed(a.seed)
    # absolute paths: ultralytics nests a relative `project` under runs/detect/
    render, work, out = Path(a.render).resolve(), Path(a.work).resolve(), Path(a.out).resolve()
    work.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    gold = json.loads((render / "GOLD_BOXES.json").read_text())
    ds, yamls = build_dataset(render, gold, work)

    model = YOLO(a.base)
    base_path = Path(getattr(model, "ckpt_path", None) or a.base)
    t0 = time.perf_counter()
    if a.reuse_run:
        run = Path(a.reuse_run).resolve()
        train_s = None
    else:
        model.train(data=str(yamls["train"]), epochs=a.epochs, imgsz=a.imgsz, seed=a.seed, deterministic=True,
                    device=a.device, workers=0, batch=8, project=str(work), name="train", exist_ok=True, plots=False,
                    verbose=False, patience=15)
        train_s = time.perf_counter() - t0
        run = Path(model.trainer.save_dir)
    best = run / "weights" / "best.pt"
    losses = []
    with open(run / "results.csv") as fh:
        for row in csv.DictReader(fh):
            row = {k.strip(): v.strip() for k, v in row.items()}
            losses.append({k: float(v) for k, v in row.items() if k in ("epoch", "train/box_loss", "train/cls_loss", "train/dfl_loss",
                                                                          "val/box_loss", "val/cls_loss", "val/dfl_loss",
                                                                          "metrics/mAP50(B)", "metrics/mAP50-95(B)")})
    det = YOLO(str(best))
    vals = {}
    for name in ("test_seen", "test_heldout"):
        m = det.val(data=str(yamls[name]), imgsz=a.imgsz, device=a.device, split="val", plots=False, verbose=False,
                    project=str(work), name=f"val_{name}", exist_ok=True)
        vals[name] = {"mAP50": round(float(m.box.map50), 4), "mAP50_95": round(float(m.box.map), 4),
                      "precision": round(float(m.box.mp), 4), "recall": round(float(m.box.mr), 4)}

    # per-field predictions + validator on every test image
    crops = work / "crops"
    crops.mkdir(exist_ok=True)
    rows, img_rows = [], []
    for img_id in sorted(gold):
        g = gold[img_id]
        if g["split"] != "test":
            continue
        img_path = render / g["image"]
        W, H = Image.open(img_path).size
        t = time.perf_counter()
        res = det.predict(str(img_path), imgsz=a.imgsz, device=a.device, conf=a.conf, verbose=False)[0]
        lat = time.perf_counter() - t
        preds = [{"bbox": [round(float(v), 1) for v in b.xyxy[0].tolist()], "conf": round(float(b.conf[0]), 4),
                  "cls": CLASSES[int(b.cls[0])]} for b in res.boxes]
        pairs = sorted(((iou(f["bbox"], p["bbox"]), gi, pi) for gi, f in enumerate(g["fields"]) for pi, p in enumerate(preds)), reverse=True)
        used_g, used_p, match = set(), set(), {}
        for v, gi, pi in pairs:
            if v >= 0.5 and gi not in used_g and pi not in used_p:
                used_g.add(gi)
                used_p.add(pi)
                match[gi] = (pi, v)
        order = sorted(range(len(preds)), key=lambda i: (round(preds[i]["bbox"][1] / 8), preds[i]["bbox"][0]))
        assignable = len(preds) == len(g["fields"])
        plan = g.get("plan_values") or {}
        img = Image.open(img_path).convert("RGB")
        for gi, f in enumerate(g["fields"]):
            assigned = preds[order[gi]] if assignable else None
            verdict, text = "ABSTAIN_BOX_COUNT", None
            if assigned:
                x1, y1, x2, y2 = assigned["bbox"]
                cp = crops / f"{Path(g['image']).stem}__{f['field_key']}.png"
                img.crop((max(0, x1 - 2), max(0, y1 - 2), min(W, x2 + 2), min(H, y2 + 2))).resize(
                    (int((x2 - x1 + 4) * 2), int((y2 - y1 + 4) * 2))).save(cp)
                text = ocr(cp, f["tag"] == "textarea")
                pv, tv = norm(plan.get(f["field_key"], "")), norm(text)
                if tv == pv:
                    verdict = "PASS"
                elif f["tag"] == "textarea" and len(tv) >= 20 and pv.startswith(tv[: max(20, len(tv) - 12)]) and len(pv) > len(tv):
                    verdict = "UNVERIFIABLE_CLIPPED"
                else:
                    verdict = "FLAG"
            m = match.get(gi)
            p = preds[m[0]] if m else None
            truth = norm(f["value"]) != norm(plan.get(f["field_key"], ""))
            rows.append({"image_id": img_id, "field_key": f["field_key"], "template_key": g["template_key"],
                         "patient_id": g["patient_id"], "held_out_layout": held_out(g),
                         "perturbation": (g.get("perturbation") or {}).get("kind"),
                         "layout": (g.get("perturbation") or {}).get("layout"),
                         "gold_bbox_px": f["bbox"], "gold_class": f["tag"],
                         "pred_bbox_px": p["bbox"] if p else None,
                         "pred_bbox_norm": [round(p["bbox"][0] / W, 5), round(p["bbox"][1] / H, 5), round(p["bbox"][2] / W, 5), round(p["bbox"][3] / H, 5)] if p else None,
                         "pred_conf": p["conf"] if p else None, "pred_class": p["cls"] if p else None,
                         "iou": round(m[1], 4) if m else 0.0, "box_found": bool(m),
                         "assigned_bbox_px": assigned["bbox"] if assigned else None,
                         "assigned_is_gold_match": bool(assigned) and bool(m) and assigned is p,
                         "ocr_text": text, "planned_value": plan.get(f["field_key"]), "written_value": f["value"],
                         "validator_verdict": verdict, "truth_written_differs_from_plan": truth})
        img_rows.append({"image_id": img_id, "n_gold": len(g["fields"]), "n_pred": len(preds),
                         "false_boxes": len(preds) - len(match), "latency_s": round(lat, 4), "held_out_layout": held_out(g)})

    def summarize(sel_rows, sel_imgs):
        n = len(sel_rows)
        pos = [r for r in sel_rows if r["truth_written_differs_from_plan"]]
        neg = [r for r in sel_rows if not r["truth_written_differs_from_plan"]]
        found = [r for r in sel_rows if r["box_found"]]
        lat = sorted(i["latency_s"] for i in sel_imgs)
        by_kind = {}
        for r in sel_rows:
            k = r["perturbation"]
            d = by_kind.setdefault(k, {"fields": 0, "mismatch_fields": 0, "flagged_mismatch": 0, "false_flags": 0, "abstain": 0})
            d["fields"] += 1
            d["abstain"] += r["validator_verdict"].startswith(("ABSTAIN", "UNVERIFIABLE"))
            if r["truth_written_differs_from_plan"]:
                d["mismatch_fields"] += 1
                d["flagged_mismatch"] += r["validator_verdict"] == "FLAG"
            else:
                d["false_flags"] += r["validator_verdict"] == "FLAG"
        return {"images": len(sel_imgs), "fields": n,
                "box_recall_iou50": round(len(found) / n, 4) if n else None,
                "mean_iou_matched": round(sum(r["iou"] for r in found) / len(found), 4) if found else None,
                "class_accuracy_matched": round(sum(r["pred_class"] == r["gold_class"] for r in found) / len(found), 4) if found else None,
                "false_boxes": sum(i["false_boxes"] for i in sel_imgs),
                "images_abstained_box_count": sum(i["n_pred"] != i["n_gold"] for i in sel_imgs),
                "reading_order_assignment_correct": round(sum(r["assigned_is_gold_match"] for r in sel_rows) / n, 4) if n else None,
                "ocr_value_agreement_clean_fields": round(sum(r["validator_verdict"] == "PASS" for r in neg) / len(neg), 4) if neg else None,
                "validator": {"mismatch_fields": len(pos),
                              "flag_recall": round(sum(r["validator_verdict"] == "FLAG" for r in pos) / len(pos), 4) if pos else None,
                              "false_flag_rate": round(sum(r["validator_verdict"] == "FLAG" for r in neg) / len(neg), 4) if neg else None,
                              "abstain_or_unverifiable_rate": round(sum(r["validator_verdict"] != "PASS" and r["validator_verdict"] != "FLAG" for r in sel_rows) / n, 4) if n else None,
                              "by_perturbation": by_kind},
                "latency_s_per_page_median": lat[len(lat) // 2] if lat else None}

    data = b"".join(json.dumps(r, sort_keys=True).encode() + b"\n" for r in rows)
    (out / "field_predictions.jsonl").write_bytes(data)
    (out / "images.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in img_rows))
    summary = {"arm": "V2-yolov8n-field-detector", "status": "EXECUTED",
               "seen_templates_test": summarize([r for r in rows if not r["held_out_layout"]], [i for i in img_rows if not i["held_out_layout"]]),
               "held_out_layout_test": summarize([r for r in rows if r["held_out_layout"]], [i for i in img_rows if i["held_out_layout"]]),
               "ultralytics_val": vals, "losses_per_epoch": losses}
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    tess = subprocess.run(["tesseract", "--version"], capture_output=True, text=True).stdout.splitlines()[0]
    counts = {}
    for g in gold.values():
        counts[g["split"]] = counts.get(g["split"], 0) + 1
    receipt = {"arm": "V2-yolov8n-field-detector", "architecture": "YOLOv8n (ultralytics), 3 classes " + "/".join(CLASSES),
               "base_checkpoint": str(a.base), "base_checkpoint_sha256": sha(base_path) if base_path.exists() else None,
               "trained_weights_sha256": sha(best), "trained_weights_bytes": best.stat().st_size,
               "weights_published": False, "images_published": False,
               "gold_boxes_sha256": sha(render / "GOLD_BOXES.json"), "jobs_sha256": sha(a.jobs) if a.jobs else None,
               "images_by_split": counts, "seed": a.seed, "epochs_requested": a.epochs, "epochs_run": len(losses),
               "imgsz": a.imgsz, "batch": 8, "patience": 15, "device": a.device, "train_seconds": round(train_s, 1) if train_s is not None else "see reused run log",
               "conf_threshold": a.conf, "ocr": tess, "field_predictions_sha256": hashlib.sha256(data).hexdigest(),
               "versions": {"ultralytics": ultralytics.__version__, "torch": torch.__version__, "python": platform.python_version()},
               "host": {"machine": platform.machine(), "platform": platform.platform()}, "hosted_inference": "NONE"}
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: summary[k] for k in ("seen_templates_test", "held_out_layout_test", "ultralytics_val")}, indent=1))


if __name__ == "__main__":
    main()
