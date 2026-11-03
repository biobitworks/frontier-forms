// Behaviour shared by every benchmark form. It stands in for what a real portal's front end does:
// controlled inputs that only count real events, comboboxes that only count a picked option, wizards that validate
// before moving on, and sections that exist only once an earlier answer reveals them. __ffRead() returns what the
// form would actually send, which is what gets scored. It is never the raw DOM value of a controlled form.
(function () {
  const S = (window.__ff = { values: {}, submitted: false });
  const controlled = document.documentElement.dataset.controlled === "1";
  const roots = () => {
    const out = [document];
    const walk = (root) => root.querySelectorAll("*").forEach((el) => {
      if (el.shadowRoot) { out.push(el.shadowRoot); walk(el.shadowRoot); }
    });
    walk(document);
    return out;
  };
  const all = (sel) => roots().flatMap((r) => [...r.querySelectorAll(sel)]);
  const fieldOf = (el) => el.closest && el.closest("[data-fid]");
  const textLike = (el) => el.matches?.("input:not([type=radio]):not([type=checkbox]),textarea");

  class Shadow extends HTMLElement {
    connectedCallback() {
      if (this.shadowRoot) return;
      const root = this.attachShadow({ mode: "open" });
      root.append(this.querySelector("template").content.cloneNode(true));
      root.append(document.getElementById("ff-style").cloneNode(true));
    }
  }

  const phone = (text) => {
    const d = text.replace(/\D/g, "").slice(0, 10);
    if (d.length < 4) return d;
    if (d.length < 7) return `(${d.slice(0, 3)}) ${d.slice(3)}`;
    return `(${d.slice(0, 3)}) ${d.slice(3, 6)}-${d.slice(6)}`;
  };

  function record(el) {
    const box = fieldOf(el);
    if (!box || box.dataset.kind === "repeat" || el.closest("[data-sub]")) return;
    if (textLike(el) && box.dataset.kind !== "combo") S.values[box.dataset.fid] = el.value;
  }

  // A controlled input is redrawn from state, so a value set without an event disappears on the next render.
  function render() {
    if (controlled) all("[data-fid] input,[data-fid] textarea").forEach((el) => {
      const box = fieldOf(el);
      if (textLike(el) && box.dataset.kind !== "combo" && !el.closest("[data-sub]") && document.activeElement !== el)
        el.value = S.values[box.dataset.fid] ?? "";
    });
    all("[data-when]").forEach((el) => {
      const [fid, value] = el.dataset.when.split(":");
      el.hidden = readField(fid) !== value;
    });
  }

  function pick(box, text) {
    S.values[box.dataset.fid] = text;
    const input = box.querySelector("input");
    input.value = text;
    input.setAttribute("aria-expanded", "false");
    box.querySelector("[role=listbox]").hidden = true;
    render();
  }

  addEventListener("input", (e) => {
    const el = e.composedPath()[0];
    if (el.dataset?.mask === "phone") el.value = phone(el.value);
    const box = fieldOf(el);
    if (box?.dataset.kind === "combo") {
      delete S.values[box.dataset.fid];
      const list = box.querySelector("[role=listbox]");
      list.hidden = false;
      el.setAttribute("aria-expanded", "true");
      const q = el.value.toLowerCase();
      list.querySelectorAll("[role=option]").forEach((o) => (o.hidden = !o.textContent.toLowerCase().includes(q)));
    }
    record(el);
    render();
  }, true);
  addEventListener("change", (e) => { record(e.composedPath()[0]); render(); }, true);

  addEventListener("focusin", (e) => {
    const el = e.composedPath()[0];
    const box = fieldOf(el);
    if (box?.dataset.kind === "combo" && el.tagName === "INPUT") {
      box.querySelector("[role=listbox]").hidden = false;
      el.setAttribute("aria-expanded", "true");
    }
  }, true);
  addEventListener("focusout", (e) => {
    const el = e.composedPath()[0];
    const box = fieldOf(el);
    if (box?.dataset.kind === "combo" && el.tagName === "INPUT")
      setTimeout(() => {  // typing alone is not an answer: leave without picking and the box clears
        if (!S.values[box.dataset.fid]) el.value = "";
        box.querySelector("[role=listbox]").hidden = true;
      }, 200);
    if (controlled) setTimeout(render, 0);
  }, true);

  addEventListener("keydown", (e) => {
    const el = e.composedPath()[0];
    const box = fieldOf(el);
    if (box?.dataset.kind === "combo" && e.key === "Enter") {
      e.preventDefault();
      const first = [...box.querySelectorAll("[role=option]")].find((o) => !o.hidden);
      if (first) pick(box, first.textContent.trim());
    }
    if (el.getAttribute?.("role") === "radio" && (e.key === " " || e.key === "Enter")) { e.preventDefault(); el.click(); }
  }, true);

  addEventListener("click", (e) => {
    const el = e.composedPath()[0];
    const option = el.closest?.("[role=option]");
    if (option) return pick(fieldOf(option), option.textContent.trim());
    const radio = el.closest?.("[role=radio]");
    if (radio) {
      radio.closest("[role=radiogroup]").querySelectorAll("[role=radio]").forEach((r) => r.setAttribute("aria-checked", "false"));
      radio.setAttribute("aria-checked", "true");
      return render();
    }
    if (el.dataset?.add !== undefined) {
      const box = fieldOf(el);
      const row = box.querySelector("template").content.firstElementChild.cloneNode(true);
      const n = box.querySelectorAll("[data-row]").length + 1;
      row.querySelectorAll("input").forEach((i) => { i.name = `${i.dataset.sub}_${n}`; });
      box.querySelector("[data-rows]").append(row);
    }
    if (el.dataset?.remove !== undefined) el.closest("[data-row]").remove();
    if (el.dataset?.nav) step(el.dataset.nav === "next" ? 1 : -1);
  }, true);

  function missingRequired(section) {
    const inRoot = [...section.querySelectorAll("[data-required]")];
    section.querySelectorAll("ff-shadow").forEach((h) => inRoot.push(...h.shadowRoot.querySelectorAll("[data-required]")));
    return inRoot.filter((box) => !box.closest("[hidden]") && isEmpty(readBox(box)));
  }

  function step(delta) {
    const steps = [...document.querySelectorAll("[data-step]")];
    const now = steps.findIndex((s) => !s.hidden);
    const missing = delta > 0 ? missingRequired(steps[now]) : [];
    const errors = document.getElementById("ff-errors");
    errors.textContent = missing.length ? `Please complete ${missing.length} required field(s) before continuing.` : "";
    if (missing.length) return;
    steps[now].hidden = true;
    steps[now + delta].hidden = false;
    document.querySelectorAll("[data-nav=back]").forEach((b) => (b.hidden = now + delta === 0));
    document.querySelectorAll("[data-nav=next]").forEach((b) => (b.hidden = now + delta === steps.length - 1));
    document.querySelectorAll("[type=submit]").forEach((b) => (b.hidden = now + delta !== steps.length - 1));
  }

  const isEmpty = (v) => v === undefined || v === null || v === "" || v === false || (Array.isArray(v) && !v.length);

  function readBox(box) {
    const fid = box.dataset.fid;
    switch (box.dataset.kind) {
      case "radio": { const on = box.querySelector("input:checked"); return on ? on.value : ""; }
      case "ariaradio": { const on = box.querySelector('[role=radio][aria-checked="true"]'); return on ? on.textContent.trim() : ""; }
      case "check": return box.querySelector("input").checked;
      case "checks": return [...box.querySelectorAll("input:checked")].map((i) => i.value);
      case "select": { const s = box.querySelector("select"); return s.selectedIndex > 0 ? s.options[s.selectedIndex].text.trim() : ""; }
      case "combo": return S.values[fid] ?? "";
      case "dateparts": {
        const [m, d, y] = [...box.querySelectorAll("select")].map((s) => s.value);
        return y && m && d ? `${y}-${m.padStart(2, "0")}-${d.padStart(2, "0")}` : "";
      }
      case "repeat":
        return [...box.querySelectorAll("[data-row]")].map((r) => Object.fromEntries([...r.querySelectorAll("input")].map((i) => [i.dataset.sub, i.value])))
          .filter((row) => Object.values(row).some((v) => v.trim()));
      default: return controlled ? S.values[fid] ?? "" : box.querySelector("input,textarea").value;
    }
  }

  function readField(fid) {
    const box = all(`[data-fid="${fid}"]`)[0];
    return box ? readBox(box) : undefined;
  }

  window.__ffRead = () => {
    render();
    const out = {};
    all("[data-fid]").forEach((box) => {
      const gate = box.closest("[data-when]");
      if (!gate || !gate.hidden) out[box.dataset.fid] = readBox(box);
    });
    document.querySelectorAll("iframe").forEach((f) => { try { Object.assign(out, f.contentWindow.__ffRead().values); } catch (_) {} });
    return { values: out, submitted: S.submitted };
  };

  addEventListener("DOMContentLoaded", () => {
    customElements.define("ff-shadow", Shadow);  // after parsing, so each element already holds its template
    const form = document.querySelector("form");
    if (form) form.addEventListener("submit", (e) => {
      e.preventDefault();
      S.submitted = true;
      navigator.sendBeacon?.("/__submitted");
    });
    render();
  });
})();
