"""Loopback-only synthetic form server with a read-only FHIR R4 facade.

Routes (all synthetic, all local):
  GET  /healthz
  GET  /forms                         list of template keys
  GET  /forms/<key>                   HTML form (no gold, no canonical keys)
  GET  /forms/<key>/schema            public schema JSON
  POST /forms/<key>/submit            JSON {patient_id, answers:[...]} -> echo
  GET  /api/patients                  synthetic patient ids + split
  GET  /api/passport/<patient_id>     teammate passport (deterministic ids)
  GET  /fhir/R4/metadata              CapabilityStatement (read/search only)
  GET  /fhir/R4/Patient/<id>
  GET  /fhir/R4/<Type>?patient=<id>   searchset Bundle

Writes to /fhir are refused (405). The server refuses to bind to anything
other than a loopback address. It never makes outbound requests.
"""
from __future__ import annotations

import ipaddress
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .passport import build_passport
from .templates import public_schema, render_html
from .acceptance_preview import render_preview_html

FHIR_SEARCH_TYPES = ("AllergyIntolerance", "Condition", "MedicationRequest", "Observation",
                     "Immunization", "Encounter", "ExplanationOfBenefit")
DECISIONS = {"fill", "needs_user_input", "needs_review", "skip"}


def capability_statement():
    return {
        "resourceType": "CapabilityStatement",
        "status": "active",
        "kind": "instance",
        "date": "2026-11-02",
        "fhirVersion": "4.0.1",
        "format": ["json"],
        "software": {"name": "frontier-forms local synthetic FHIR facade", "version": "1"},
        "implementation": {"description": "Loopback-only, synthetic MITRE Synthea data. Read/search only."},
        "rest": [{
            "mode": "server",
            "resource": [{"type": "Patient", "interaction": [{"code": "read"}]}]
            + [{"type": t, "interaction": [{"code": "search-type"}],
                "searchParam": [{"name": "patient", "type": "reference"}]} for t in FHIR_SEARCH_TYPES],
        }],
    }


class FormState:
    def __init__(self, members, bundles, templates):
        self.members = {m.patient_id: m for m in members}
        self.bundles = bundles
        self.templates = templates
        self.submissions = []
        self._passports = {}
        self._lock = threading.Lock()

    def passport(self, pid):
        with self._lock:
            if pid not in self._passports:
                m = self.members[pid]
                self._passports[pid] = build_passport(self.bundles[pid], m.path.name, f"SYN-{pid[:8]}")
            return self._passports[pid]


def make_handler(state: FormState):
    class Handler(BaseHTTPRequestHandler):
        server_version = "FrontierFormsLocal/1"

        def log_message(self, *args):  # keep test output and receipts clean
            pass

        def _send(self, code, body, ctype="application/json"):
            data = body if isinstance(body, bytes) else (
                json.dumps(body, sort_keys=True).encode() if ctype.endswith("json") else body.encode())
            self.send_response(code)
            self.send_header("Content-Type", ctype + "; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _err(self, code, msg):
            self._send(code, {"error": msg})

        def do_GET(self):
            u = urlparse(self.path)
            parts = [p for p in u.path.split("/") if p]
            q = parse_qs(u.query)
            if parts == ["healthz"]:
                return self._send(200, {"ok": True, "synthetic_only": True})
            if parts == ["forms"]:
                return self._send(200, sorted(state.templates))
            if len(parts) == 3 and parts[:2] == ["preview", "forms"]:
                t = state.templates.get(parts[2])
                if not t:
                    return self._err(404, "UNKNOWN_TEMPLATE")
                return self._send(200, render_preview_html(t), "text/html")
            if len(parts) in (2, 3) and parts[0] == "forms":
                t = state.templates.get(parts[1])
                if not t:
                    return self._err(404, "UNKNOWN_TEMPLATE")
                if len(parts) == 2:
                    return self._send(200, render_html(t), "text/html")
                if parts[2] == "schema":
                    return self._send(200, public_schema(t))
            if parts == ["api", "patients"]:
                return self._send(200, [{"patient_id": m.patient_id, "split": m.split}
                                        for m in state.members.values()])
            if len(parts) == 3 and parts[:2] == ["api", "passport"]:
                if parts[2] not in state.members:
                    return self._err(404, "UNKNOWN_PATIENT")
                return self._send(200, state.passport(parts[2]))
            if parts[:2] == ["fhir", "R4"]:
                return self._fhir(parts[2:], q)
            return self._err(404, "NOT_FOUND")

        def _fhir(self, rest, q):
            ctype = "application/fhir+json"
            if rest == ["metadata"]:
                return self._send(200, capability_statement(), ctype)
            if len(rest) == 2 and rest[0] == "Patient":
                b = state.bundles.get(rest[1])
                if not b:
                    return self._send(404, {"resourceType": "OperationOutcome", "issue": [
                        {"severity": "error", "code": "not-found"}]}, ctype)
                pat = next(e["resource"] for e in b["entry"] if e["resource"]["resourceType"] == "Patient")
                return self._send(200, pat, ctype)
            if len(rest) == 1 and rest[0] in FHIR_SEARCH_TYPES:
                pid = (q.get("patient") or [""])[0].removeprefix("Patient/")
                b = state.bundles.get(pid)
                if not b:
                    return self._send(400, {"resourceType": "OperationOutcome", "issue": [
                        {"severity": "error", "code": "required",
                         "diagnostics": "patient search parameter required"}]}, ctype)
                res = [e["resource"] for e in b["entry"] if e["resource"]["resourceType"] == rest[0]]
                return self._send(200, {"resourceType": "Bundle", "type": "searchset", "total": len(res),
                                        "entry": [{"resource": r, "search": {"mode": "match"}} for r in res]},
                                  ctype)
            return self._send(404, {"resourceType": "OperationOutcome", "issue": [
                {"severity": "error", "code": "not-supported"}]}, ctype)

        def do_POST(self):
            u = urlparse(self.path)
            parts = [p for p in u.path.split("/") if p]
            if parts[:1] == ["fhir"]:
                return self._err(405, "FHIR_WRITE_PROHIBITED")
            if len(parts) == 3 and parts[0] == "forms" and parts[2] == "submit":
                t = state.templates.get(parts[1])
                if not t:
                    return self._err(404, "UNKNOWN_TEMPLATE")
                n = int(self.headers.get("Content-Length") or 0)
                if n > 1_000_000:
                    return self._err(413, "TOO_LARGE")
                try:
                    body = json.loads(self.rfile.read(n))
                except ValueError:
                    return self._err(400, "INVALID_JSON")
                if body.get("patient_id") not in state.members:
                    return self._err(400, "UNKNOWN_PATIENT")
                allowed = {f["field_key"] for f in t["fields"]}
                answers = body.get("answers") or []
                keys = [a.get("field_key") for a in answers]
                if any(k not in allowed for k in keys) or len(set(keys)) != len(keys):
                    return self._err(422, "FIELD_KEY_CONTRACT_VIOLATION")
                if any(a.get("decision") not in DECISIONS for a in answers):
                    return self._err(422, "DECISION_CONTRACT_VIOLATION")
                record = {"template_key": t["template_key"], "patient_id": body["patient_id"],
                          "answers": sorted(answers, key=lambda a: a["field_key"])}
                with state._lock:
                    state.submissions.append(record)
                return self._send(200, {"accepted": True, **record})
            return self._err(405, "METHOD_NOT_ALLOWED")

        do_PUT = do_DELETE = do_PATCH = lambda self: self._err(405, "METHOD_NOT_ALLOWED")

    return Handler


def serve(state: FormState, host: str = "127.0.0.1", port: int = 0) -> ThreadingHTTPServer:
    if not ipaddress.ip_address(host).is_loopback:
        raise ValueError("LOOPBACK_ONLY")
    httpd = ThreadingHTTPServer((host, port), make_handler(state))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd
