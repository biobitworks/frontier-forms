"""The benchmark's form suite, written as data and rendered to static HTML.

Each `F` names the gold concept it asks for (see passports.gold) but the rendered page carries no trace of it. Labels are
paraphrased per form, so nothing learned from a dev form's wording transfers by string match. Dev forms are the only ones
used while building the tools. Test forms stay held out, and they include widgets the tools were not developed on:
iframes, date parts, ARIA radio grids and header-labelled table matrices.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent

YN = {"Yes": "yes", "No": "no"}
YNU = {"Yes": "yes", "No": "no", "Unknown": None}
SEX = {"Male": "male", "Female": "female"}
SEX_FULL = {"Male": "male", "Female": "female", "Intersex": "other", "Prefer not to say": None}
MARITAL = {"Single": "single", "Married": "married", "Divorced": "divorced", "Widowed": "widowed", "Separated": "separated"}
RACE = {"White": "white", "Black or African American": "black or african american", "Asian": "asian",
        "American Indian or Alaska Native": "american indian or alaska native",
        "Native Hawaiian or Other Pacific Islander": "native hawaiian or other pacific islander", "Other": "other",
        "Decline to state": None}
ETHNIC = {"Hispanic or Latino": "hispanic", "Not Hispanic or Latino": "not hispanic", "Decline to state": None}
LANGUAGE = {"English": "english", "Spanish": "spanish", "Portuguese": "portuguese", "Mandarin": "mandarin",
            "Haitian Creole": "haitian", "Other": "other"}
INSURER = {"Aetna": "aetna", "Anthem": "anthem", "Blue Cross Blue Shield": "blue cross blue shield", "Cigna Health": "cigna health",
           "Dual Eligible": "dual eligible", "Humana": "humana", "Kaiser Permanente": "kaiser", "Medicaid": "medicaid", "Medicare": "medicare",
           "Tricare": "tricare", "UnitedHealthcare": "unitedhealthcare", "Self-pay / no insurance": "uninsured", "Other": None}
SMOKE = {"Never": "never", "Former": "former", "Current": "current"}
SMOKE2 = {"Have never smoked": "never", "Quit smoking": "former", "Smoke now": "current"}
RELATION = {"Spouse": "spouse", "Parent": "parent", "Sibling": "sibling", "Child": "child", "Friend": "friend", "Other": None}
ALCOHOL = {"None": "none", "Occasional": "occasional", "Weekly": "weekly", "Daily": "daily"}
STATE = {"California": "CA", "Connecticut": "CT", "Florida": "FL", "Maine": "ME", "Massachusetts": "MA", "New Hampshire": "NH",
         "New York": "NY", "Rhode Island": "RI", "Texas": "TX", "Vermont": "VT"}


@dataclass
class F:
    gold: str
    label: str
    kind: str = "text"
    options: dict | None = None
    required: bool = False
    hint: str = ""
    when: tuple | None = None
    fmt: str = ""
    rows: list | None = None  # matrix: (gold, label) pairs
    sub: list | None = None  # repeat: (key, label) columns
    fid: str = ""


@dataclass
class Section:
    title: str
    fields: list
    intro: str = ""
    shadow: bool = False
    iframe: bool = False


@dataclass
class Form:
    name: str
    title: str
    split: str
    track: str
    sections: list
    layout: str = "for"
    controlled: bool = False
    opaque: bool = False
    wizard: bool = False
    notes: str = ""

    def fields(self) -> list:
        return [f for s in self.sections for f in s.fields]

    def scored(self) -> list[tuple[str, F, str]]:
        """(field id, field, gold key), with one entry per matrix row."""
        out = []
        for f in self.fields():
            if f.kind in ("matrix", "ariamatrix"):
                out += [(f"{f.fid}_{i}", f, key) for i, (key, _) in enumerate(f.rows)]
            else:
                out.append((f.fid, f, f.gold))
        return out

    def features(self) -> list[str]:
        kinds = {f.kind for f in self.fields()}
        tags = [k for k in ("combo", "repeat", "matrix", "ariamatrix", "dateparts", "phonemask") if k in kinds]
        tags += [t for t, on in (("controlled", self.controlled), ("wizard", self.wizard), ("conditional", any(f.when for f in self.fields())),
                                 ("shadow-dom", any(s.shadow for s in self.sections)), ("iframe", any(s.iframe for s in self.sections))) if on]
        return tags


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:26].rstrip("_")


def _assign_ids(form: Form) -> None:
    if form.fields()[0].fid:
        return
    n = 0
    seen = {}
    for f in form.fields():
        n += 1
        base = f"q{n}" if form.opaque else _slug(f.label)
        seen[base] = seen.get(base, 0) + 1
        f.fid = base if seen[base] == 1 else f"{base}_{seen[base]}"
    names = {f.gold: f.fid for f in form.fields()}
    for f in form.fields():  # `when` refers to its gate by gold key, resolved here.
        if f.when:
            f.when = (names[f.when[0]], f.when[1], f.when[0], f.when[2] if len(f.when) > 2 else f.when[1].lower())


# --- rendering ------------------------------------------------------------------------------------------------------

def _labelled(form: Form, f: F, control: str, input_id: str) -> str:
    text = escape(f.label) + (' <span class="req">*</span>' if f.required else "")
    hint = f'<div class="hint">{escape(f.hint)}</div>' if f.hint else ""
    if form.layout == "wrap":
        return f"<label>{text} {control}</label>{hint}"
    if form.layout == "table":
        return f"<tr><th>{text}</th><td>{control}{hint}</td></tr>"
    if form.layout == "aria":
        return f'<div class="lbl" id="l_{input_id}">{text}</div>{control.replace("<input", f"""<input aria-labelledby="l_{input_id}" """, 1).replace("<textarea", f"""<textarea aria-labelledby="l_{input_id}" """, 1).replace("<select", f"""<select aria-labelledby="l_{input_id}" """, 1)}{hint}'
    if form.layout == "placeholder":
        return control.replace("<input", f"""<input placeholder="{escape(f.label, quote=True)}" """, 1).replace("<textarea", f"""<textarea placeholder="{escape(f.label, quote=True)}" """, 1) + hint
    return f'<label for="{input_id}">{text}</label>{control}{hint}'


def _choices(f: F, input_type: str) -> str:
    return "".join(f'<label class="choice"><input type="{input_type}" name="{f.fid}" value="{escape(o, quote=True)}"> {escape(o)}</label>'
                   for o in f.options)


def _field(form: Form, f: F) -> str:
    fid, attrs = f.fid, f'data-fid="{f.fid}" data-kind="{f.kind}"' + (" data-required" if f.required else "")
    legend = escape(f.label) + (' <span class="req">*</span>' if f.required else "")
    hint = f'<div class="hint">{escape(f.hint)}</div>' if f.hint else ""
    if f.kind == "textarea":
        body = _labelled(form, f, f'<textarea id="{fid}" name="{fid}" rows="3"></textarea>', fid)
    elif f.kind in ("text", "email", "tel", "number", "date"):
        body = _labelled(form, f, f'<input id="{fid}" name="{fid}" type="{f.kind}">', fid)
    elif f.kind == "phonemask":
        body = _labelled(form, f, f'<input id="{fid}" name="{fid}" type="tel" data-mask="phone" inputmode="numeric">', fid)
    elif f.kind == "select":
        options = '<option value="">Choose one</option>' + "".join(f"<option>{escape(o)}</option>" for o in f.options)
        body = _labelled(form, f, f'<select id="{fid}" name="{fid}">{options}</select>', fid)
    elif f.kind == "radio":
        body = f'<fieldset><legend>{legend}</legend>{_choices(f, "radio")}{hint}</fieldset>'
    elif f.kind == "checks":
        body = f'<fieldset><legend>{legend}</legend>{_choices(f, "checkbox")}{hint}</fieldset>'
    elif f.kind == "check":
        body = f'<label class="choice"><input type="checkbox" name="{fid}"> {legend}</label>{hint}'
    elif f.kind == "combo":
        items = "".join(f'<li role="option">{escape(o)}</li>' for o in f.options)
        control = (f'<input id="{fid}" role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="{fid}_list" autocomplete="off">'
                   f'<ul id="{fid}_list" role="listbox" hidden>{items}</ul>')
        body = _labelled(form, f, control, fid)
    elif f.kind == "dateparts":
        months = "".join(f'<option value="{i}">{m}</option>' for i, m in enumerate(
            "January February March April May June July August September October November December".split(), 1))
        days = "".join(f'<option value="{d}">{d}</option>' for d in range(1, 32))
        years = "".join(f'<option value="{y}">{y}</option>' for y in range(2026, 1909, -1))
        body = (f'<fieldset><legend>{legend}</legend><select aria-label="Month"><option value="">Month</option>{months}</select>'
                f'<select aria-label="Day"><option value="">Day</option>{days}</select>'
                f'<select aria-label="Year"><option value="">Year</option>{years}</select>{hint}</fieldset>')
    elif f.kind == "repeat":
        inputs = "".join(f'<label>{escape(label)} <input data-sub="{key}"></label>' for key, label in f.sub)
        row = f'<div class="row" data-row>{inputs}<button type="button" data-remove>Remove</button></div>'
        first = row.replace('data-sub="', 'name="_0" data-sub="')
        rows = re.sub(r'name="_0" data-sub="(\w+)"', r'name="\1_1" data-sub="\1"', first)
        body = (f'<fieldset><legend>{legend}</legend>{hint}<div data-rows>{rows}</div>'
                f'<template>{row}</template><button type="button" data-add>+ {escape(f.hint or "Add another")}</button></fieldset>')
        body = body.replace(hint, "", 1) if hint else body
    elif f.kind == "matrix":  # columns are labelled only by the header row, as on paper-derived forms
        head = "".join(f"<th>{escape(o)}</th>" for o in f.options)
        rows = ""
        for i, (_, label) in enumerate(f.rows):
            cells = "".join(f'<td><input type="radio" name="{fid}_{i}" value="{escape(o, quote=True)}"></td>' for o in f.options)
            rows += f'<tr data-fid="{fid}_{i}" data-kind="radio"><th scope="row">{escape(label)}</th>{cells}</tr>'
        return f'<div class="field"><p>{legend}</p><table class="matrix"><thead><tr><th></th>{head}</tr></thead><tbody>{rows}</tbody></table></div>'
    elif f.kind == "ariamatrix":
        rows = ""
        for i, (_, label) in enumerate(f.rows):
            buttons = "".join(f'<div role="radio" tabindex="0" aria-checked="false">{escape(o)}</div>' for o in f.options)
            rows += (f'<div class="gridrow" data-fid="{fid}_{i}" data-kind="ariaradio"><span id="{fid}_{i}_l">{escape(label)}</span>'
                     f'<div role="radiogroup" aria-labelledby="{fid}_{i}_l">{buttons}</div></div>')
        return f'<div class="field"><p>{legend}</p>{rows}</div>'
    elif f.kind == "hidden":
        return f'<div class="field offscreen" aria-hidden="true" data-fid="{fid}" data-kind="text"><label>{escape(f.label)} <input name="{fid}" tabindex="-1" autocomplete="off"></label></div>'
    else:
        raise ValueError(f.kind)
    if form.layout == "table" and f.kind in ("text", "email", "tel", "number", "date", "phonemask", "select", "textarea", "combo"):
        return body.replace("<tr>", f"<tr {attrs}>", 1)
    return f'<div class="field" {attrs}>{body}</div>'


def _tabled(parts: list[str]) -> str:
    """A <tr> outside a <table> is discarded by the HTML parser, so runs of rows are wrapped together."""
    html, rows = "", []
    for part in parts + [""]:
        if part.startswith("<tr"):
            rows.append(part)
            continue
        if rows:
            html += f"<table>{''.join(rows)}</table>"
            rows = []
        html += part
    return html


def _gated(form: Form, fields: list) -> str:
    parts, i = [], 0
    while i < len(fields):
        f = fields[i]
        if not f.when:
            parts.append(_field(form, f))
            i += 1
            continue
        group = []
        while i < len(fields) and fields[i].when and fields[i].when[:2] == f.when[:2]:
            group.append(fields[i])
            i += 1
        inner = _tabled([_field(form, g) for g in group])
        parts.append(f'<div data-when="{f.when[0]}:{escape(f.when[1], quote=True)}" hidden>{inner}</div>')
    return _tabled(parts)


def _section(form: Form, s: Section, n: int) -> str:
    body = _gated(form, s.fields)
    intro = f'<p class="intro">{escape(s.intro)}</p>' if s.intro else ""
    if s.shadow:
        body = f"<ff-shadow><template>{body}</template></ff-shadow>"
    if s.iframe:
        body = f'<iframe title="{escape(s.title, quote=True)}" src="part{n}.html"></iframe>'
    step = f' data-step="{n}"' + (" hidden" if n else "") if form.wizard else ""
    return f"<section{step}><h2>{escape(s.title)}</h2>{intro}{body}</section>"


STYLE = """<style id="ff-style">
body{font:16px/1.4 system-ui,sans-serif;max-width:860px;margin:24px auto;padding:0 16px;color:#1b2430}
h1{font-size:24px}h2{font-size:18px;border-bottom:1px solid #d5dbe3;padding-bottom:4px;margin-top:28px}
.field{margin:12px 0}label,.lbl{display:block;font-weight:600;margin-bottom:3px}.choice{display:inline-block;font-weight:400;margin-right:14px}
input:not([type=radio]):not([type=checkbox]),select,textarea{font:inherit;padding:6px;width:100%;max-width:420px;box-sizing:border-box}
fieldset{border:1px solid #d5dbe3;margin:12px 0}.hint{color:#5b6675;font-size:13px}.req{color:#b3261e}
table{border-collapse:collapse;width:100%}th{text-align:left;font-weight:600;padding:5px 8px}td{padding:5px 8px}.matrix td{text-align:center}
[role=listbox]{list-style:none;margin:0;padding:0;border:1px solid #aab;max-height:180px;overflow:auto;max-width:420px;background:#fff}
[role=option]{padding:5px 8px;cursor:pointer}[role=option]:hover{background:#e6eefc}[hidden]{display:none!important}
.gridrow{display:flex;gap:16px;align-items:center;padding:4px 0}[role=radiogroup]{display:flex;gap:8px}
[role=radio]{border:1px solid #aab;border-radius:4px;padding:2px 12px;cursor:pointer}[role=radio][aria-checked=true]{background:#1d4ed8;color:#fff}
.offscreen{position:absolute;left:-9999px}iframe{width:100%;height:420px;border:1px solid #d5dbe3}.row{display:flex;gap:8px;align-items:end;margin:6px 0}
#ff-errors{color:#b3261e;font-weight:600}.intro{color:#37424f}
</style>"""


def render(form: Form) -> dict[str, str]:
    """{file name: contents} for one form's static site."""
    _assign_ids(form)
    head = f'<!doctype html><html lang="en" data-controlled="{int(form.controlled)}"><head><meta charset="utf-8"><title>{escape(form.title)}</title>{STYLE}<script src="runtime.js"></script></head>'
    sections = "".join(_section(form, s, i) for i, s in enumerate(form.sections))
    nav = '<div id="ff-errors" role="alert"></div>'
    if form.wizard:
        nav += '<button type="button" data-nav="back" hidden>Back</button> <button type="button" data-nav="next">Next</button> <button type="submit" hidden>Submit</button>'
    else:
        nav += '<button type="submit">Submit</button>'
    notice = "<p class=\"hint\">Synthetic benchmark form. Not a real provider.</p>"
    pages = {"index.html": f"{head}<body><h1>{escape(form.title)}</h1>{notice}<form novalidate>{sections}{nav}</form></body></html>"}
    for i, s in enumerate(form.sections):
        if s.iframe:
            pages[f"part{i}.html"] = f"{head}<body>{_gated(form, s.fields)}</body></html>"
    return pages


# --- the forms ------------------------------------------------------------------------------------------------------

def dev_forms() -> list[Form]:
    primary = Form("primary_care_registration", "Oakline Family Medicine: New Patient Registration", "dev", "medical", [
        Section("About you", [
            F("first", "First name", required=True), F("middle", "Middle name"), F("last", "Last name", required=True),
            F("dob", "Date of birth", "date", required=True),
            F("sex", "Sex assigned at birth", "radio", SEX), F("marital", "Marital status", "select", MARITAL),
            F("race", "Race", "select", RACE), F("ethnicity", "Ethnicity", "select", ETHNIC),
            F("language", "Preferred language", "select", LANGUAGE), F("occupation", "Occupation"), F("employer", "Employer"),
        ]),
        Section("How to reach you", [
            F("street", "Street address"), F("city", "City"), F("state", "State", "select", STATE), F("zip", "ZIP code"),
            F("phone", "Phone number", "tel"), F("email", "Email address", "email"),
            F("ec_name", "Emergency contact name"), F("ec_relation", "Relationship to you", "select", RELATION),
            F("ec_phone", "Emergency contact phone", "tel"),
        ]),
        Section("Health summary", [
            F("pcp", "Referring physician"), F("pharmacy", "Preferred pharmacy"),
            F("active_meds", "List the medications you take now", "textarea", hint="Prescription and over the counter"),
            F("allergies", "Known allergies", "textarea", hint="Write none if you have no known allergies"),
            F("smoking", "Tobacco use", "radio", SMOKE),
            F("surgeries", "Past surgeries, with year", "textarea"),
            F("reason", "Reason for today's visit", "textarea"),
        ]),
        Section("Sign here", [F("signature", "Patient signature (type full name to sign)"), F("office", "Office use only: chart number")]),
    ])
    urgent = Form("urgent_care_history", "Beacon Urgent Care: Medical History", "dev", "medical", [
        Section("Patient", [
            F("full_name", "Patient name", required=True), F("dob", "Birthdate", hint="MM/DD/YYYY", fmt="MM/DD/YYYY", required=True),
            F("sex", "Gender at birth", "select", SEX_FULL), F("phone", "Best phone", "phonemask"), F("pcp", "Primary doctor"),
        ]),
        Section("Medical history", [
            F("dx", "Have you ever been told you have any of the following?", "matrix", YN,
              rows=[("dx_diabetes", "Diabetes"), ("dx_hypertension", "High blood pressure"), ("dx_asthma", "Asthma"),
                    ("dx_heart", "Heart disease"), ("dx_cancer", "Cancer"), ("dx_kidney", "Kidney disease"), ("dx_depression", "Depression")]),
            F("takes_meds", "Do you currently take any medicines?", "radio", YN),
            F("active_meds", "Which medicines?", "textarea", when=("takes_meds", "Yes")),
            F("has_allergy", "Any allergies?", "radio", YN),
            F("allergies", "List your allergies", "textarea", when=("has_allergy", "Yes")),
            F("pregnant", "Could you be pregnant?", "radio", YNU), F("smoking", "Smoking", "select", SMOKE),
            F("alcohol", "Alcohol use", "select", ALCOHOL),
        ]),
        Section("Vitals on record", [
            F("height_cm", "Height (cm)", "number"), F("weight_kg", "Weight (kg)", "number"),
            F("bp_sys", "Blood pressure, systolic", "number"), F("bp_dia", "Blood pressure, diastolic", "number"),
        ]),
    ], layout="table")
    insurance = Form("insurance_update", "Harborview Clinic: Insurance and Contact Update", "dev", "medical", [
        Section("Who is updating", [F("first", "Given name", required=True), F("last", "Family name", required=True),
                                    F("dob", "Date of birth", "date", required=True), F("ssn4", "Last 4 of SSN")]),
        Section("Coverage", [F("insurer", "Insurance company", "combo", INSURER), F("member_id", "Member ID"), F("group_no", "Group number"),
                             F("pharmacy", "Pharmacy on file"), F("pharmacy_phone", "Pharmacy phone", "tel")]),
        Section("Contact", [F("street", "Home address"), F("city", "Town or city"), F("state", "State", "combo", STATE), F("zip", "Postal code"),
                            F("email", "Email", "email"), F("ec_name", "Who should we call in an emergency?"), F("ec_phone", "Their phone number", "tel")]),
    ], wizard=True, controlled=True)
    rental = Form("rental_application", "Parkside Residences: Rental Application", "dev", "general", [
        Section("Applicant", [F("full_name", "Applicant full name", required=True), F("dob", "Date of birth", "date"), F("phone", "Mobile"), F("email", "Email")]),
        Section("Residence", [F("street", "Current address"), F("city", "City"), F("state", "State", "select", STATE), F("zip", "ZIP"),
                              F("landlord", "Current landlord name"), F("landlord_phone", "Landlord phone"), F("rent", "Current monthly rent (USD)", "number")]),
        Section("Employment", [F("employer", "Current employer"), F("occupation", "Job title"), F("income", "Gross monthly income (USD)", "number")]),
        Section("Vehicle", [F("car_make", "Car make"), F("car_model", "Car model"), F("plate", "License plate")]),
        Section("Authorization", [F("signature", "Applicant signature"), F("office", "For office use: unit assigned")]),
    ], layout="wrap")
    return [primary, urgent, insurance, rental]


def test_forms() -> list[Form]:
    specialty = Form("specialty_medication_intake", "Northshore Allergy and Immunology: Medication Intake", "test", "medical", [
        Section("Identify the patient", [
            F("first", "Legal first name", required=True), F("last", "Legal surname", required=True),
            F("dob", "Birth date (MM/DD/YYYY)", fmt="MM/DD/YYYY", required=True), F("language", "Language spoken at home", "combo", LANGUAGE),
            F("insurer", "Health plan", "combo", INSURER), F("member_id", "Subscriber number"),
        ]),
        Section("Medications", [
            F("active_meds", "Enter every medicine you are on at this time. Do not include ones you have stopped.", "repeat",
              sub=[("name", "Medicine"), ("dose", "Strength"), ("freq", "How often")], hint="Add medicine"),
            F("pharmacy", "Where do you fill prescriptions?"),
        ]),
        Section("Allergy profile", [
            F("has_drug_allergy", "Has any drug ever caused an allergic reaction?", "radio", YN),
            F("drug_allergies", "Name each drug", "textarea", when=("has_drug_allergy", "Yes")),
            F("food_allergies", "Foods that cause a reaction", "textarea", hint="Leave blank if none known"),
            F("allergies", "All known allergies of any kind", "textarea"),
            F("dx_asthma", "Asthma diagnosis?", "radio", YN),
            F("smoking", "Cigarette history", "radio", SMOKE2),
        ]),
    ], layout="aria", controlled=True, opaque=True)
    cardio = Form("cardiology_previsit", "Summit Heart Center: Pre-Visit Questionnaire", "test", "medical", [
        Section("Demographics", [
            F("full_name", "Name as on your ID", required=True), F("dob", "When were you born?", "dateparts", required=True),
            F("age", "Age", "number"), F("sex", "Biological sex", "radio", SEX), F("phone", "Daytime telephone", "phonemask"),
            F("pcp", "Who is your regular doctor?"),
        ]),
        Section("Measurements", [
            F("height_ft", "Height: feet", "number", hint="Whole feet only. Convert from your chart if needed."),
            F("height_in", "Height: inches", "number", hint="Inches past the whole feet"),
            F("weight_lb", "Weight in pounds", "number", hint="Round to the nearest pound"),
            F("pulse", "Resting pulse", "number"), F("bp_sys", "Top blood pressure number", "number"),
            F("bp_dia", "Bottom blood pressure number", "number"), F("bmi", "Body mass index", "number"),
        ]),
        Section("Cardiac history", [
            F("dxs", "Mark each condition you have now or have had in the past", "ariamatrix", YN,
              rows=[("dx_hypertension", "Elevated blood pressure"), ("dx_heart", "Coronary or other heart disease"), ("dx_stroke", "Stroke"),
                    ("dx_diabetes", "Diabetes of any type"), ("dx_obesity", "Obesity"), ("dx_kidney", "Chronic kidney problems")]),
            F("fam", "Blood relatives with these conditions", "matrix", YN,
              rows=[("fh_heart", "Heart disease"), ("fh_diabetes", "Diabetes"), ("fh_cancer", "Cancer")]),
            F("active_meds", "Current drug regimen", "textarea", hint="Only medicines you take now"),
            F("smoking", "Have you smoked?", "select", SMOKE), F("exercise", "How often do you exercise?", "select",
              {"None": "none", "1-2 times per week": "1-2 times per week", "3 or more times per week": "3 or more times per week"}),
            F("symptom", "Do you get chest pain when you climb stairs?", "radio", YN),
        ]),
    ], layout="for", controlled=True)
    preadmit = Form("hospital_preadmission", "St. Aldric Hospital: Pre-Admission Packet", "test", "medical", [
        Section("Step 1: Patient", [
            F("first", "Patient first name", required=True), F("last", "Patient last name", required=True),
            F("dob", "Patient date of birth", "date", required=True), F("sex", "Sex", "select", SEX), F("ssn", "Social Security number"),
            F("marital", "Current marital status", "select", MARITAL), F("race", "Race (for federal reporting)", "combo", RACE),
        ]),
        Section("Step 2: Next of kin", [
            F("ec_name", "Name of next of kin"), F("ec_relation", "Their relationship to the patient", "select", RELATION),
            F("ec_phone", "Next of kin telephone", "phonemask"),
        ], shadow=True),
        Section("Step 3: Coverage", [
            F("insurer", "Primary payer", "select", INSURER), F("member_id", "Policy number"), F("group_no", "Group ID"),
        ], shadow=True),
        Section("Step 4: Clinical", [
            F("takes_meds", "Does the patient take any medicine now?", "radio", YN),
            F("active_meds", "Enter the medicines", "repeat", sub=[("name", "Drug name"), ("dose", "Dose")], hint="Another medicine",
              when=("takes_meds", "Yes")),
            F("allergies", "Allergies and reactions", "textarea"), F("surgeries", "Previous operations", "textarea"),
            F("advance_directive", "Does the patient have an advance directive?", "radio", YNU),
            F("pregnant", "Pregnancy status", "radio", YNU), F("flu_date", "Date of most recent flu shot", "date"),
        ]),
        Section("Step 5: Acknowledgement", [
            F("signature", "I attest the above is true (patient signature)"), F("office", "Registrar initials (staff only)"),
        ]),
    ], layout="for", wizard=True, controlled=True, opaque=True)
    telehealth = Form("telehealth_consent", "Lumen Virtual Care: Registration and Consent", "test", "medical", [
        Section("Your details", [
            F("first", "First name", required=True), F("last", "Last name", required=True), F("dob", "DOB (MM/DD/YYYY)", fmt="MM/DD/YYYY", required=True),
            F("email", "Email"), F("phone", "Cell"), F("state", "State where you will be during visits"), F("zip", "ZIP"),
        ]),
        Section("Clinical snapshot", [
            F("reason", "What would you like help with?", "textarea"), F("active_meds", "Medicines you take", "textarea"),
            F("allergies", "Allergies", "textarea"), F("pharmacy", "Pharmacy for e-prescriptions"), F("pharmacy_phone", "Pharmacy telephone"),
        ], iframe=True),
        Section("Consent", [
            F("signature", "Type your name to consent to telehealth treatment"), F("office", "Clinician ID (staff use)"),
            F("honeypot", "Leave this field empty", "hidden"),
        ]),
    ], layout="placeholder", controlled=False)
    behavioral = Form("behavioral_health_intake", "Greenfield Counseling: Intake Questionnaire", "test", "medical", [
        Section("About you", [
            F("full_name", "Your name", required=True), F("dob", "Your birthday", "date", required=True), F("sex", "Sex", "radio", SEX),
            F("marital", "Relationship status", "radio", MARITAL), F("occupation", "What do you do for work?"), F("employer", "Where do you work?"),
            F("insurer", "Insurance", "select", INSURER),
        ]),
        Section("Over the past two weeks", [
            F("mood", "How often have you been bothered by the following?", "matrix",
              {"Not at all": None, "Several days": "several", "More than half the days": "half", "Nearly every day": "nearly"},
              rows=[("symptom", "Little interest or pleasure in doing things"), ("symptom", "Feeling down or hopeless"),
                    ("symptom", "Trouble falling or staying asleep"), ("symptom", "Feeling tired or having little energy"),
                    ("symptom", "Poor appetite or overeating"), ("symptom", "Trouble concentrating")],
              ),
        ], intro="These questions are about how you feel. Only you can answer them."),
        Section("Health background", [
            F("dx_depression", "Ever diagnosed with depression?", "radio", YN), F("dx_anxiety", "Ever diagnosed with an anxiety disorder?", "radio", YN),
            F("active_meds", "Medications, including psychiatric ones", "textarea"), F("alcohol", "How much do you drink?", "select", ALCOHOL),
            F("reason", "What brings you in?", "textarea"),
        ]),
    ], layout="wrap")
    long_form = Form("hospital_full_registration", "Meridian Regional: Full Registration Record", "test", "medical", [
        Section("A. Identity", [
            F("first", "Given name", required=True), F("middle", "Middle"), F("last", "Surname", required=True), F("dob", "Birth date", "date", required=True),
            F("age", "Age in years", "number"), F("sex", "Sex at birth", "select", SEX_FULL), F("marital", "Marital", "select", MARITAL),
            F("race", "Race category", "select", RACE), F("ethnicity", "Hispanic origin", "radio", ETHNIC), F("language", "Primary language", "select", LANGUAGE),
            F("ssn", "SSN"), F("occupation", "Occupation or trade"), F("employer", "Employer name"),
        ]),
        Section("B. Address and contact", [
            F("street", "Mailing street"), F("city", "Mailing city"), F("state", "Mailing state", "select", STATE), F("zip", "Mailing ZIP"),
            F("phone", "Home telephone", "phonemask"), F("email", "E-mail"),
        ]),
        Section("C. Contacts and care team", [
            F("ec_name", "Person to notify"), F("ec_relation", "Relation", "select", RELATION), F("ec_phone", "Notify at phone"),
            F("pcp", "Attending primary physician"), F("pharmacy", "Community pharmacy"), F("pharmacy_phone", "Pharmacy phone no."),
        ]),
        Section("D. Insurance", [F("insurer", "Carrier", "select", INSURER), F("member_id", "ID number on card"), F("group_no", "Group")]),
        Section("E. Vitals", [
            F("height_cm", "Stature (cm)", "number"), F("weight_kg", "Mass (kg)", "number"), F("bmi", "BMI", "number"), F("pulse", "Heart rate (bpm)", "number"),
            F("bp_sys", "Systolic BP", "number"), F("bp_dia", "Diastolic BP", "number"),
        ]),
        Section("F. Problem list", [
            F("probs", "Check Yes or No for each", "matrix", YN,
              rows=[("dx_diabetes", "Diabetes mellitus"), ("dx_hypertension", "Hypertension"), ("dx_asthma", "Asthma"), ("dx_copd", "COPD, emphysema or chronic bronchitis"),
                    ("dx_heart", "Cardiac disease"), ("dx_stroke", "CVA or stroke"), ("dx_cancer", "Malignancy"), ("dx_depression", "Depression"),
                    ("dx_anxiety", "Anxiety"), ("dx_kidney", "Renal disease"), ("dx_arthritis", "Arthritis"), ("dx_obesity", "Obesity")]),
            F("fam2", "Family history", "matrix", YNU, rows=[("fh_heart", "Cardiac disease in a parent"), ("fh_diabetes", "Diabetes in a parent"), ("fh_cancer", "Cancer in a parent")]),
        ]),
        Section("G. Medications, allergies, immunizations", [
            F("active_meds", "Home medication list", "textarea"), F("allergies", "Allergy list", "textarea"),
            F("had_flu_shot", "Has had an influenza vaccine", "radio", YN), F("had_covid_shot", "Has had a COVID-19 vaccine", "radio", YN),
            F("flu_date", "Last influenza vaccine date", "date"),
        ]),
        Section("H. Social", [
            F("smoking", "Tobacco", "select", SMOKE), F("alcohol", "Alcohol", "select", ALCOHOL),
            F("exercise", "Exercise", "select", {"None": "none", "1-2 times per week": "1-2 times per week", "3 or more times per week": "3 or more times per week"}),
            F("surgeries", "Surgical history", "textarea"), F("advance_directive", "Advance directive on file", "radio", YNU),
        ]),
        Section("I. Certification", [F("signature", "Signature of patient or guardian"), F("office", "Admitting clerk ID")]),
    ], layout="table", opaque=True)
    claim = Form("auto_insurance_claim", "Crestline Mutual: First Notice of Loss", "test", "general", [
        Section("Policyholder", [F("full_name", "Policyholder name", required=True), F("dob", "Policyholder date of birth", "dateparts"),
                                 F("phone", "Contact number", "phonemask"), F("email", "Contact email"), F("street", "Garaging address"), F("city", "Garaging city"),
                                 F("state", "Garaging state", "combo", STATE), F("zip", "Garaging ZIP")]),
        Section("Vehicle involved", [F("car_year", "Model year", "number"), F("car_make", "Manufacturer"), F("car_model", "Model"), F("plate", "Registration plate")]),
        Section("The incident", [F("reason", "Describe what happened", "textarea"), F("symptom", "Was anyone hurt?", "radio", YN), F("signature", "Claimant signature")]),
    ], layout="aria", controlled=True, wizard=True, opaque=True)
    enroll = Form("university_enrollment", "Ashbury College: Continuing Education Enrollment", "test", "general", [
        Section("Student", [F("first", "Student first name", required=True), F("last", "Student last name", required=True), F("dob", "Student birth date", "date"),
                            F("sex", "Sex", "radio", SEX), F("race", "Race", "select", RACE), F("ethnicity", "Ethnicity", "select", ETHNIC),
                            F("language", "First language", "combo", LANGUAGE)]),
        Section("Contact", [F("street", "Home street"), F("city", "Home city"), F("state", "Home state", "select", STATE), F("zip", "Home ZIP"), F("email", "Personal email"),
                            F("phone", "Personal phone")]),
        Section("Background", [F("school", "Last school attended"), F("grad_year", "Year completed", "number"), F("occupation", "Current occupation"), F("employer", "Current employer"),
                               F("reason", "Why do you want to enroll?", "textarea")]),
        Section("Emergency", [F("ec_name", "Emergency contact"), F("ec_phone", "Emergency phone"), F("signature", "Student signature"), F("office", "Registrar use: student number")]),
    ], layout="wrap", controlled=True)
    return [specialty, cardio, preadmit, telehealth, behavioral, long_form, claim, enroll]


def all_forms() -> dict[str, Form]:
    forms = {f.name: f for f in dev_forms() + test_forms()}
    for form in forms.values():
        render(form)  # assigns stable field ids
    return forms


def build_site(out: Path) -> None:
    """Write only what a browser may see: the pages and runtime.js. Schemas and gold stay in harness/data."""
    runtime = (HERE / "runtime.js").read_text()
    links = []
    for name, form in all_forms().items():
        folder = out / name
        folder.mkdir(parents=True, exist_ok=True)
        for filename, html in render(form).items():
            (folder / filename).write_text(html)
        (folder / "runtime.js").write_text(runtime)
        links.append(f'<li><a href="{name}/">{escape(form.title)}</a></li>')
    (out / "index.html").write_text(f'<!doctype html><meta charset="utf-8"><title>Benchmark forms</title><h1>Synthetic benchmark forms</h1><ul>{"".join(links)}</ul>')


if __name__ == "__main__":
    for form in all_forms().values():
        print(f"{form.split:5} {form.track:8} {form.name:30} fields={len(form.scored()):3} {form.layout:12} {' '.join(form.features())}")
