"""Deterministic draft-FHIR mapping and scoring for the synthetic encounter-intake form.

Scope: Synthea-derived SYNTHETIC forms only. Produces draft FHIR R4 Patient and Encounter
resources from extracted form fields. No EHR connection, no write-back, no clinical use.

Every function here is pure and deterministic so the same extracted fields always produce
byte-identical drafts. The scorer compares a draft to a gold-derived draft field by field and
returns counts with explicit NULL denominators instead of 0.0 when a class is empty.
"""
from __future__ import annotations
import hashlib, json, re
from typing import Dict, Optional

FORM_FIELDS = ('Synthetic case', 'Patient first', 'Patient last', 'Birth date', 'Gender', 'Encounter date', 'Visit class')
GENDER_MAP = {'f': 'female', 'female': 'female', 'm': 'male', 'male': 'male'}
# HL7 v3 ActCode class mapping for the synthetic visit classes used by the renderer.
VISIT_CLASS_MAP = {'wellness': 'AMB', 'ambulatory': 'AMB', 'outpatient': 'AMB', 'emergency': 'EMER',
                   'inpatient': 'IMP', 'urgentcare': 'AMB', 'urgent care': 'AMB'}
ISO_DATE = re.compile(r'^(\d{4})-(\d{2})-(\d{2})$')


def canon(o) -> bytes:
    return json.dumps(o, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def normalize_field(name: str, value: Optional[str]) -> Optional[str]:
    """Deterministic normalization used by both the extractor scorer and the mapper."""
    if value is None:
        return None
    v = re.sub(r'\s+', ' ', str(value)).strip()
    if v == '':
        return None
    if name in ('Birth date', 'Encounter date'):
        v = v.replace('/', '-').replace('.', '-')
        m = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})$', v)
        if m:
            return f'{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}'
        return v
    if name == 'Gender':
        return GENDER_MAP.get(v.lower(), v.lower())
    if name == 'Visit class':
        return v.lower()
    if name == 'Synthetic case':
        return v.lower()
    return v


def validate_fields(fields: Dict[str, Optional[str]], expected_case_id: Optional[str] = None) -> Dict[str, str]:
    """Deterministic admission checks per field. Returns {field: 'OK' | reason}."""
    out = {}
    for f in FORM_FIELDS:
        v = normalize_field(f, fields.get(f))
        if v is None:
            out[f] = 'MISSING'
        elif f in ('Birth date', 'Encounter date') and not ISO_DATE.match(v):
            out[f] = 'INVALID_DATE'
        elif f == 'Gender' and v not in ('male', 'female'):
            out[f] = 'INVALID_GENDER'
        elif f == 'Synthetic case' and expected_case_id is not None and v != expected_case_id.lower():
            out[f] = 'CASE_ID_MISMATCH_WITH_FCO'
        else:
            out[f] = 'OK'
    if out.get('Birth date') == 'OK' and out.get('Encounter date') == 'OK':
        if normalize_field('Encounter date', fields['Encounter date']) < normalize_field('Birth date', fields['Birth date']):
            out['Encounter date'] = 'ENCOUNTER_BEFORE_BIRTH'
    return out


def draft_fhir(fields: Dict[str, Optional[str]], source_fco_id: str) -> Dict:
    """Draft FHIR R4 Patient + Encounter. Identifiers derive from the source FCO, never from PHI."""
    n = {f: normalize_field(f, fields.get(f)) for f in FORM_FIELDS}
    pid = 'synthetic-' + hashlib.sha256(canon([source_fco_id, 'patient'])).hexdigest()[:16]
    eid = 'synthetic-' + hashlib.sha256(canon([source_fco_id, 'encounter'])).hexdigest()[:16]
    patient = {'resourceType': 'Patient', 'id': pid,
               'meta': {'tag': [{'system': 'urn:frontier-forms:synthetic', 'code': 'SYNTHETIC_NOT_CLINICAL'}]},
               'identifier': [{'system': 'urn:frontier-forms:fco', 'value': source_fco_id}],
               'name': [{'given': [n['Patient first']] if n['Patient first'] else [], 'family': n['Patient last']}],
               'gender': n['Gender'] if n['Gender'] in ('male', 'female') else 'unknown',
               'birthDate': n['Birth date'] if n['Birth date'] and ISO_DATE.match(n['Birth date']) else None}
    encounter = {'resourceType': 'Encounter', 'id': eid, 'status': 'finished',
                 'class': {'system': 'http://terminology.hl7.org/CodeSystem/v3-ActCode',
                           'code': VISIT_CLASS_MAP.get(n['Visit class'] or '', 'AMB')},
                 'subject': {'reference': 'Patient/' + pid},
                 'period': {'start': n['Encounter date']} if n['Encounter date'] else {}}
    return {'resourceType': 'Bundle', 'type': 'collection', 'entry': [{'resource': patient}, {'resource': encounter}],
            'meta': {'tag': [{'system': 'urn:frontier-forms:writeback', 'code': 'PROHIBITED'}]}}


def score_fields(pred: Dict[str, Optional[str]], gold: Dict[str, Optional[str]]):
    """Per-field exact match after normalization. Returns flags (no values)."""
    return {f: normalize_field(f, pred.get(f)) == normalize_field(f, gold.get(f)) for f in FORM_FIELDS}


def confusion(admitted: Dict[str, bool], correct: Dict[str, bool]):
    """Field-level admission confusion. Positive = admitted. FP = admitted but wrong (false admission)."""
    tp = sum(1 for f in FORM_FIELDS if admitted.get(f) and correct.get(f))
    fp = sum(1 for f in FORM_FIELDS if admitted.get(f) and not correct.get(f))
    fn = sum(1 for f in FORM_FIELDS if not admitted.get(f) and correct.get(f))
    tn = sum(1 for f in FORM_FIELDS if not admitted.get(f) and not correct.get(f))
    div = lambda a, b: (a / b) if b else None
    return {'TP': tp, 'FP': fp, 'FN': fn, 'TN': tn, 'FPR': div(fp, fp + tn), 'FDR': div(fp, tp + fp),
            'FNR': div(fn, tp + fn), 'precision': div(tp, tp + fp), 'recall': div(tp, tp + fn),
            'AUROC': 'NOT_COMPUTED_NO_CONTINUOUS_SCORES'}
