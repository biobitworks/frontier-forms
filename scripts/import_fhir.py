"""Import Synthea FHIR R4 patient bundles into Supabase.

Normalizes each bundle into one `patient_passports` row, the `source_records`
that back each fact (raw FHIR payload kept for provenance), and typed
`passport_facts`. Re-running is idempotent: passports are upserted by
synthetic_id and their source records/facts are replaced.

Usage:
    .venv/bin/python scripts/import_fhir.py <bundle_dir> --limit 100

Fact keys produced:
    allergy.{medication,food,environment,biologic}
    condition.active, condition.resolved
    medication.active, medication.past
    immunization.history
    vitals.{height,weight,bmi,blood_pressure,heart_rate}
    social.smoking_status
    insurance.primary
"""

import argparse
import json
import os
import re
import uuid
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb

DATASET_LABEL = "synthea-sample-data-fhir-latest"

# LOINC code -> fact_key (latest observation only)
VITALS = {
    "8302-2": "vitals.height",
    "29463-7": "vitals.weight",
    "39156-5": "vitals.bmi",
    "85354-9": "vitals.blood_pressure",
    "8867-4": "vitals.heart_rate",
    "72166-2": "social.smoking_status",
}
BP_SYSTOLIC, BP_DIASTOLIC = "8480-6", "8462-4"

PATIENT_FILE = re.compile(r"_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.json$")


def strip_digits(name):
    """Synthea appends numeric suffixes to names (e.g. 'Hackett68')."""
    return re.sub(r"\d+$", "", name) if name else name


def first_coding(concept):
    codings = (concept or {}).get("coding") or [{}]
    return codings[0]


def code_token(concept):
    c = first_coding(concept)
    return f"{c['system']}|{c['code']}" if c.get("code") else None


def concept_text(concept):
    return (concept or {}).get("text") or first_coding(concept).get("display")


def semantic_tag(display):
    """SNOMED display suffix, e.g. 'Essential hypertension (disorder)' -> 'disorder'."""
    m = re.search(r"\(([^()]+)\)\s*$", display or "")
    return m.group(1) if m else None


def extension(resource, url_suffix):
    for ext in resource.get("extension", []):
        if ext["url"].endswith(url_suffix):
            return ext
    return None


def omb_text(resource, url_suffix):
    ext = extension(resource, url_suffix)
    if not ext:
        return None
    for sub in ext.get("extension", []):
        if sub["url"] == "text":
            return sub["valueString"]
    return None


class PassportBuilder:
    def __init__(self, bundle, source_file):
        self.source_file = source_file
        self.by_type = {}
        self.by_urn = {}
        for entry in bundle["entry"]:
            r = entry["resource"]
            self.by_type.setdefault(r["resourceType"], []).append(r)
            self.by_urn[entry.get("fullUrl") or f"urn:uuid:{r['id']}"] = r
        self.patient = self.by_type["Patient"][0]
        self.source_records = []
        self.facts = []

    def resources(self, rtype):
        return self.by_type.get(rtype, [])

    def add_source(self, resource, clinical_code=None, effective_at=None):
        payload = {k: v for k, v in resource.items() if k != "text"}
        source_id = str(uuid.uuid4())
        self.source_records.append({
            "id": source_id,
            "fhir_resource_type": resource["resourceType"],
            "fhir_resource_id": resource["id"],
            "clinical_code": clinical_code,
            "effective_at": effective_at,
            "source_file_path": self.source_file,
            "payload": payload,
        })
        return source_id

    def add_fact(self, fact_key, value, source_id, value_type="object",
                 status="known", valid_from=None, valid_until=None):
        self.facts.append({
            "id": str(uuid.uuid4()),
            "source_record_id": source_id,
            "fact_key": fact_key,
            "value": value,
            "value_type": value_type,
            "status": status,
            "valid_from": valid_from,
            "valid_until": valid_until,
        })

    # -- passport row -------------------------------------------------------

    def passport_row(self, synthetic_id):
        p = self.patient
        name = next((n for n in p.get("name", []) if n.get("use") == "official"), p["name"][0])
        given = [strip_digits(g) for g in name.get("given", [])]
        family = strip_digits(name.get("family"))
        maiden = next((strip_digits(n.get("family")) for n in p.get("name", [])
                       if n.get("use") == "maiden"), None)
        ssn = next((i["value"] for i in p.get("identifier", [])
                    if i.get("system") == "http://hl7.org/fhir/sid/us-ssn"), None)
        addr = (p.get("address") or [{}])[0]
        phone = next((t["value"] for t in p.get("telecom", []) if t.get("system") == "phone"), None)
        language = concept_text((p.get("communication") or [{}])[0].get("language"))
        birthsex = extension(p, "us-core-birthsex")
        birthplace = extension(p, "patient-birthPlace")

        demographics = {
            "synthea_patient_id": p["id"],
            "dataset": DATASET_LABEL,
            "prefix": (name.get("prefix") or [None])[0],
            "given_name": given[0] if given else None,
            "middle_names": given[1:],
            "family_name": family,
            "maiden_name": maiden,
            "date_of_birth": p.get("birthDate"),
            "gender": p.get("gender"),
            "birth_sex": birthsex["valueCode"] if birthsex else None,
            "race": omb_text(p, "us-core-race"),
            "ethnicity": omb_text(p, "us-core-ethnicity"),
            "marital_status": concept_text(p.get("maritalStatus")),
            "preferred_language": language,
            "birth_place": birthplace["valueAddress"] if birthplace else None,
            "synthetic_ssn": ssn,
        }
        contact = {
            "phone": phone,
            "address": {
                "line": addr.get("line", []),
                "city": addr.get("city"),
                "state": addr.get("state"),
                "postal_code": addr.get("postalCode"),
                "country": addr.get("country"),
            },
        }
        display_name = " ".join(x for x in [given[0] if given else None, family] if x)
        return {
            "synthetic_id": synthetic_id,
            "display_name": display_name,
            "demographics": demographics,
            "contact": contact,
            "insurance": self.insurance(),
        }

    # -- facts ----------------------------------------------------------------

    def build_facts(self):
        self.allergies()
        self.conditions()
        self.medications()
        self.immunizations()
        self.vitals()

    def allergies(self):
        for a in self.resources("AllergyIntolerance"):
            category = (a.get("category") or ["unknown"])[0]
            clinical = first_coding(a.get("clinicalStatus")).get("code")
            reactions = [
                {"manifestation": concept_text(m), "severity": rx.get("severity")}
                for rx in a.get("reaction", []) for m in rx.get("manifestation", [])
            ]
            src = self.add_source(a, code_token(a.get("code")), a.get("recordedDate"))
            self.add_fact(
                f"allergy.{category}",
                {
                    "substance": concept_text(a.get("code")),
                    "type": a.get("type"),
                    "criticality": a.get("criticality"),
                    "clinical_status": clinical,
                    "reactions": reactions,
                },
                src,
                status="known" if clinical == "active" else "expired",
                valid_from=a.get("recordedDate"),
            )

    def conditions(self):
        for c in self.resources("Condition"):
            clinical = first_coding(c.get("clinicalStatus")).get("code")
            display = concept_text(c.get("code"))
            src = self.add_source(c, code_token(c.get("code")), c.get("onsetDateTime"))
            self.add_fact(
                "condition.active" if clinical == "active" else "condition.resolved",
                {
                    "name": display,
                    "code": code_token(c.get("code")),
                    "semantic_tag": semantic_tag(display),
                    "clinical_status": clinical,
                    "onset": c.get("onsetDateTime"),
                    "abatement": c.get("abatementDateTime"),
                },
                src,
                valid_from=c.get("onsetDateTime"),
                valid_until=c.get("abatementDateTime"),
            )

    def medication_concept(self, req):
        if "medicationCodeableConcept" in req:
            return req["medicationCodeableConcept"]
        ref = req.get("medicationReference", {}).get("reference")
        med = self.by_urn.get(ref)
        return med.get("code") if med else None

    def medications(self):
        for m in self.resources("MedicationRequest"):
            concept = self.medication_concept(m)
            dosage = (m.get("dosageInstruction") or [{}])[0]
            repeat = dosage.get("timing", {}).get("repeat", {})
            dose = (dosage.get("doseAndRate") or [{}])[0].get("doseQuantity", {})
            src = self.add_source(m, code_token(concept), m.get("authoredOn"))
            self.add_fact(
                "medication.active" if m["status"] == "active" else "medication.past",
                {
                    "name": concept_text(concept),
                    "code": code_token(concept),
                    "request_status": m["status"],
                    "dose_quantity": dose.get("value"),
                    "frequency": repeat.get("frequency"),
                    "period": repeat.get("period"),
                    "period_unit": repeat.get("periodUnit"),
                    "as_needed": dosage.get("asNeededBoolean"),
                    "reason": [r.get("display") for r in m.get("reasonReference", [])],
                    "authored_on": m.get("authoredOn"),
                },
                src,
                valid_from=m.get("authoredOn"),
            )

    def immunizations(self):
        for i in self.resources("Immunization"):
            src = self.add_source(i, code_token(i.get("vaccineCode")), i.get("occurrenceDateTime"))
            self.add_fact(
                "immunization.history",
                {
                    "vaccine": concept_text(i.get("vaccineCode")),
                    "code": code_token(i.get("vaccineCode")),
                    "date": i.get("occurrenceDateTime"),
                    "status": i.get("status"),
                },
                src,
                valid_from=i.get("occurrenceDateTime"),
            )

    def vitals(self):
        """Most recent final observation per tracked LOINC code."""
        latest = {}
        for o in self.resources("Observation"):
            loinc = first_coding(o.get("code")).get("code")
            if loinc not in VITALS or o.get("status") not in ("final", "amended"):
                continue
            when = o.get("effectiveDateTime") or ""
            if loinc not in latest or when > (latest[loinc].get("effectiveDateTime") or ""):
                latest[loinc] = o
        for loinc, o in latest.items():
            when = o.get("effectiveDateTime")
            if loinc == "85354-9":
                comps = {first_coding(c["code"]).get("code"): c.get("valueQuantity", {})
                         for c in o.get("component", [])}
                value = {
                    "systolic": comps.get(BP_SYSTOLIC, {}).get("value"),
                    "diastolic": comps.get(BP_DIASTOLIC, {}).get("value"),
                    "unit": comps.get(BP_SYSTOLIC, {}).get("unit"),
                    "observed_at": when,
                }
            elif "valueCodeableConcept" in o:
                value = {"value": concept_text(o["valueCodeableConcept"]),
                         "code": code_token(o["valueCodeableConcept"]),
                         "observed_at": when}
            else:
                q = o.get("valueQuantity", {})
                value = {"value": q.get("value"), "unit": q.get("unit"), "observed_at": when}
            src = self.add_source(o, f"http://loinc.org|{loinc}", when)
            self.add_fact(VITALS[loinc], value, src, valid_from=when)

    def insurance(self):
        """Payer from the most recent ExplanationOfBenefit (Synthea has no Coverage resources)."""
        eobs = self.resources("ExplanationOfBenefit")
        if not eobs:
            return {}
        eob = max(eobs, key=lambda e: e.get("billablePeriod", {}).get("start") or e.get("created") or "")
        payer = eob.get("insurer", {}).get("display")
        as_of = eob.get("billablePeriod", {}).get("start") or eob.get("created")
        src = self.add_source(eob, None, as_of)
        has_coverage = payer not in (None, "NO_INSURANCE")
        value = {"payer": payer if has_coverage else None, "uninsured": not has_coverage, "as_of": as_of}
        self.add_fact("insurance.primary", value, src, valid_from=as_of)
        return {**value, "source": "ExplanationOfBenefit"}


def select_bundles(bundle_dir, limit, include_deceased):
    picked = []
    for path in sorted(Path(bundle_dir).glob("*.json"), key=lambda p: p.name.rsplit("_", 1)[-1]):
        if not PATIENT_FILE.search(path.name):
            continue  # hospitalInformation*/practitionerInformation* bundles
        bundle = json.loads(path.read_text())
        patient = next(e["resource"] for e in bundle["entry"]
                       if e["resource"]["resourceType"] == "Patient")
        if not include_deceased and ("deceasedDateTime" in patient or patient.get("deceasedBoolean")):
            continue
        picked.append((path, bundle))
        if len(picked) == limit:
            break
    return picked


def import_bundle(conn, synthetic_id, path, bundle):
    builder = PassportBuilder(bundle, f"{DATASET_LABEL}/{path.name}")
    passport = builder.passport_row(synthetic_id)
    builder.build_facts()

    with conn.cursor() as cur:
        cur.execute(
            """
            insert into public.patient_passports
              (synthetic_id, display_name, demographics, contact, insurance)
            values (%s, %s, %s, %s, %s)
            on conflict (synthetic_id) do update set
              display_name = excluded.display_name,
              demographics = excluded.demographics,
              contact = excluded.contact,
              insurance = excluded.insurance,
              updated_at = now()
            returning id
            """,
            (passport["synthetic_id"], passport["display_name"], Jsonb(passport["demographics"]),
             Jsonb(passport["contact"]), Jsonb(passport["insurance"])),
        )
        passport_id = cur.fetchone()[0]
        cur.execute("delete from public.passport_facts where passport_id = %s", (passport_id,))
        cur.execute("delete from public.source_records where passport_id = %s", (passport_id,))
        cur.executemany(
            """
            insert into public.source_records
              (id, passport_id, fhir_resource_type, fhir_resource_id, clinical_code,
               effective_at, source_file_path, payload)
            values (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            [(s["id"], passport_id, s["fhir_resource_type"], s["fhir_resource_id"],
              s["clinical_code"], s["effective_at"], s["source_file_path"], Jsonb(s["payload"]))
             for s in builder.source_records],
        )
        cur.executemany(
            """
            insert into public.passport_facts
              (id, passport_id, source_record_id, fact_key, value, value_type, status,
               valid_from, valid_until)
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            [(f["id"], passport_id, f["source_record_id"], f["fact_key"], Jsonb(f["value"]),
              f["value_type"], f["status"], f["valid_from"], f["valid_until"])
             for f in builder.facts],
        )
    return passport["display_name"], len(builder.source_records), len(builder.facts)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("bundle_dir")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--include-deceased", action="store_true",
                        help="Living patients only by default (intake forms assume a living patient).")
    args = parser.parse_args()

    load_dotenv(".env.local")
    load_dotenv(".env")
    bundles = select_bundles(args.bundle_dir, args.limit, args.include_deceased)
    print(f"Importing {len(bundles)} patient bundles from {args.bundle_dir}")

    with psycopg.connect(os.environ["DATABASE_URL"], sslmode="require") as conn:
        for n, (path, bundle) in enumerate(bundles, start=1):
            synthetic_id = f"SYN-{n:05d}"
            with conn.transaction():
                name, n_src, n_facts = import_bundle(conn, synthetic_id, path, bundle)
            print(f"  {synthetic_id}  {name:<30} {n_src:5} sources {n_facts:5} facts")


if __name__ == "__main__":
    main()
