"""inspect_form: read a page into a form schema, from what any web page exposes: labels, ARIA, tables and legends."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

EXTRACT = r"""() => {
  const deep = (root, out = []) => { root.querySelectorAll('*').forEach((el) => { out.push(el); if (el.shadowRoot) deep(el.shadowRoot, out); }); return out; };
  const els = deep(document);
  const squash = (t) => (t || '').replace(/\s+/g, ' ').replace(/\s*\*\s*$/, '').trim();
  const up = (el) => el.parentElement || (el.getRootNode() && el.getRootNode().host) || null;
  const shown = (el) => {
    for (let n = el; n; n = up(n)) {
      if (n.hidden || n.getAttribute?.('aria-hidden') === 'true') return false;
      const s = getComputedStyle(n);
      if (s.display === 'none' || s.visibility === 'hidden') return false;
    }
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && r.right > 0 && r.left > -1000;
  };
  const byId = (el, id) => el.getRootNode().getElementById?.(id) || document.getElementById(id);
  const quote = (v) => String(v).replace(/\\/g, '\\\\').replace(/"/g, '\\"');
  const ownText = (label) => {
    const copy = label.cloneNode(true);
    copy.querySelectorAll('input,select,textarea,ul,button').forEach((c) => c.remove());
    return squash(copy.textContent);
  };
  const named = (el) => {
    const ids = el.getAttribute('aria-labelledby');
    if (ids) { const t = ids.split(/\s+/).map((i) => byId(el, i)?.textContent || '').join(' '); if (squash(t)) return squash(t); }
    if (el.getAttribute('aria-label')) return squash(el.getAttribute('aria-label'));
    if (el.labels && el.labels.length) { const t = ownText(el.labels[0]); if (t) return t; }
    const wrap = el.closest('label'); if (wrap) { const t = ownText(wrap); if (t) return t; }
    const cell = el.closest('td'); const head = cell?.parentElement?.querySelector('th');
    if (head) return squash(head.textContent);
    return squash(el.getAttribute('placeholder') || el.title || '');
  };
  const legend = (el) => { const f = el.closest('fieldset'); return f ? squash(f.querySelector('legend')?.textContent) : ''; };
  const section = (el) => {
    for (let n = el; n; n = up(n)) if (n.tagName === 'SECTION') return squash(n.querySelector('h1,h2,h3,legend')?.textContent);
    return '';
  };
  const hint = (el) => {
    const described = el.getAttribute('aria-describedby');
    if (described) return squash(byId(el, described)?.textContent);
    const start = el.closest('label') || el;
    for (const node of [start.nextElementSibling, el.closest('fieldset')?.querySelector('legend')?.nextElementSibling]) {
      if (node && !node.matches('input,select,textarea,label,button,fieldset,table,ul') && !node.querySelector('input,select,textarea') && node.textContent.length < 160) return squash(node.textContent);
    }
    return '';
  };
  const required = (el) => el.required || el.getAttribute('aria-required') === 'true' || /\*\s*$/.test((el.labels?.[0]?.textContent || '').trim());
  // A control with no name or id gets a mark of our own, kept between inspections so its key stays stable.
  const tag = (el) => { el.dataset.ffMark ||= String(window.__ffMarks = (window.__ffMarks || 0) + 1); return `[data-ff-mark="${el.dataset.ffMark}"]`; };
  const selector = (el) => {
    if (el.name) return `${el.tagName.toLowerCase()}[name="${quote(el.name)}"]`;
    if (el.id) return `[id="${quote(el.id)}"]`;
    if (el.getAttribute('aria-labelledby')) return `[aria-labelledby="${quote(el.getAttribute('aria-labelledby'))}"]`;
    return tag(el);
  };
  const fields = [];
  const taken = new Set();

  // Repeating rows: an "Add ..." button beside one or more sets of inputs.
  for (const btn of els.filter((e) => e.tagName === 'BUTTON' && /^\+?\s*(add|another)\b/i.test(squash(e.textContent)) && shown(e))) {
    const box = btn.closest('fieldset') || btn.parentElement;
    const inputs = [...box.querySelectorAll('input,textarea')].filter(shown);
    if (!inputs.length) continue;
    const row = inputs[0].closest('tr,li') || inputs[0].closest('label')?.parentElement || inputs[0].parentElement;
    const cols = inputs.filter((i) => row.contains(i));
    const rows = [...row.parentElement.children].filter((r) => r.matches?.(row.tagName) && r.querySelector('input,textarea'));
    inputs.forEach((i) => taken.add(i));
    fields.push({ type: 'repeat', label: legend(inputs[0]) || squash(box.querySelector('p')?.textContent), section: section(box), required: false,
      selector: tag(btn), columns: cols.map(named), hint: hint(inputs[0]), options: [],
      value: rows.map((r) => [...r.querySelectorAll('input,textarea')].map((i) => i.value)).filter((r) => r.some(Boolean)) , rows: rows.length });
  }

  const groups = new Map();
  for (const el of els) {
    if (taken.has(el) || !shown(el)) continue;
    if (el.matches('input[type=radio],input[type=checkbox]')) {
      const key = `${el.type}:${el.name}`;
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(el);
    } else if (el.matches('[role=radiogroup]')) {
      const options = [...el.querySelectorAll('[role=radio]')];
      fields.push({ type: 'ariaradio', label: named(el), question: squash(el.closest('div')?.parentElement?.parentElement?.querySelector('p')?.textContent), section: section(el), required: false,
        selector: selector(el), options: options.map((o) => squash(o.textContent)), hint: '',
        value: squash(options.find((o) => o.getAttribute('aria-checked') === 'true')?.textContent) });
    } else if (el.matches('input[role=combobox]')) {
      const list = byId(el, el.getAttribute('aria-controls'));
      fields.push({ type: 'combobox', label: named(el), section: section(el), required: required(el), selector: selector(el), hint: hint(el), value: el.value,
        options: list ? [...list.querySelectorAll('[role=option]')].map((o) => squash(o.textContent)) : [] });
    } else if (el.matches('select')) {
      const opts = [...el.options].filter((o) => o.value !== '' || o.text.trim());
      const real = opts.filter((o, i) => !(i === 0 && (o.value === '' || /^(choose|select)/i.test(o.text))));
      fields.push({ type: 'select', label: named(el), group: legend(el), section: section(el), required: required(el), selector: selector(el), hint: hint(el),
        options: real.map((o) => squash(o.text)), value: el.selectedIndex > 0 ? squash(el.options[el.selectedIndex].text) : '' });
    } else if (el.matches('textarea,input') && !el.matches('input[type=hidden],input[type=submit],input[type=button],input[type=file],input[type=reset]')) {
      fields.push({ type: el.tagName === 'TEXTAREA' ? 'textarea' : (el.type || 'text'), label: named(el), section: section(el), required: required(el), selector: selector(el), hint: hint(el), value: el.value, options: [] });
    }
  }
  for (const [key, members] of groups) {
    const first = members[0];
    const cell = first.closest('td'); const tr = cell?.parentElement;
    const inRow = tr && [...tr.querySelectorAll('input')].length > 1 && tr.querySelector('th');
    const heads = inRow ? [...tr.closest('table').querySelectorAll('thead th')].map((t) => squash(t.textContent)) : [];
    const optionText = (el) => {
      if (inRow) return heads[[...tr.children].indexOf(el.closest('td'))] || el.value;
      const t = el.labels?.[0] ? ownText(el.labels[0]) : ''; return t || el.value;
    };
    const lone = first.type === 'checkbox' && members.length === 1;
    const question = inRow ? squash(tr.closest('table').parentElement.querySelector('p')?.textContent) : '';
    fields.push({ type: lone ? 'checkbox' : first.type === 'radio' ? 'radio' : 'checks', label: inRow ? squash(tr.querySelector('th').textContent) : lone ? ownText(first.labels[0]) : legend(first),
      question, section: section(first), required: required(first), hint: hint(first), selector: `input[name="${quote(first.name)}"]`,
      options: lone ? [] : members.map(optionText), values: members.map((m) => m.value),
      value: lone ? first.checked : first.type === 'radio' ? (members.filter((m) => m.checked).map(optionText)[0] || '') : members.filter((m) => m.checked).map(optionText) });
  }
  const buttons = els.filter((e) => (e.tagName === 'BUTTON' || e.matches('input[type=button],input[type=submit]')) && shown(e));
  const next = buttons.find((b) => b.type !== 'submit' && /^(next|continue)\b/i.test(squash(b.textContent || b.value)));
  if (next) next.dataset.ffNext = '1';
  const alert = els.filter((e) => e.getAttribute('role') === 'alert').map((e) => squash(e.textContent)).filter(Boolean)[0] || '';
  return { fields: fields.filter((f) => f.selector && (f.label || f.question)), has_next: !!next, alert, title: document.title };
}"""


@dataclass
class Field:
    key: str
    type: str
    label: str
    selector: str
    frame: int
    section: str = ""
    question: str = ""
    group: str = ""
    hint: str = ""
    required: bool = False
    options: list = field(default_factory=list)
    values: list = field(default_factory=list)
    columns: list = field(default_factory=list)
    rows: int = 0
    value: object = ""

    def asked(self) -> str:
        return " / ".join(part for part in (self.section, self.question, self.group, self.label) if part)

    def public(self) -> dict:
        row = {"field_key": self.key, "question": self.asked(), "type": self.type}
        if self.hint:
            row["hint"] = self.hint
        if self.options:
            row["options"] = self.options
        if self.columns:
            row["columns"] = self.columns
        return row


@dataclass
class FormSchema:
    fields: list
    has_next: bool
    alert: str
    frames: list

    def to_dict(self) -> dict:
        return {"fields": [asdict(f) for f in self.fields], "has_next": self.has_next, "alert": self.alert}


def inspect_form(page) -> FormSchema:
    """One schema across the page and its same-origin frames. Each field's key stays the same between inspections."""
    fields, has_next, alert, frames = [], False, "", list(page.frames)
    for index, frame in enumerate(frames):
        try:
            found = frame.evaluate(EXTRACT)
        except Exception:
            continue
        has_next = has_next or (found["has_next"] and index == 0)
        alert = alert or found["alert"]
        for row in found["fields"]:
            row = {k: v for k, v in row.items() if k in Field.__dataclass_fields__}
            fields.append(Field(key=f"{index}|{row['selector']}", frame=index, **row))
    return FormSchema(fields, has_next, alert, frames)
