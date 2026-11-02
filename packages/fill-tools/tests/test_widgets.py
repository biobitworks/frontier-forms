"""Widgets the dev forms do not contain, on a fixture of their own. No model and no benchmark form is involved."""
import http.server, functools, sys, threading
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from fill_tools.apply_form import apply_field
from fill_tools.inspect_form import inspect_form
from fill_tools.validate import never_fill

# The tools may use only what any web page exposes, never the markers the benchmark's forms and scorer rely on.
for source in (HERE.parent / "fill_tools").glob("*.py"):
    text = source.read_text()
    for marker in ("data-fid", "data-kind", "data-required", "data-step", "data-when", "data-sub", "data-row", "data-nav", "__ffRead", "__ff.", "bench/harness"):
        assert marker not in text, f"{source.name} uses benchmark marker {marker}"

CHROME = Path.home() / "Library/Caches/ms-playwright/chromium-1223/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(HERE))
handler.log_message = lambda *a, **k: None
server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=str(CHROME), headless=True)
    page = browser.new_page()
    page.goto(f"http://127.0.0.1:{server.server_address[1]}/widgets.html")
    page.wait_for_timeout(300)
    schema = inspect_form(page)
    by = {f.label: f for f in schema.fields}
    print({f.label: f.type for f in schema.fields})
    assert "Leave empty" not in by and "trap" not in str(schema.to_dict()), "off-screen trap must not be offered"
    assert never_fill(by["Patient signature"])
    apply_field(page, by["Month"], "March")
    apply_field(page, by["Year"], "2020")
    apply_field(page, by["Hay fever"], "No")
    apply_field(page, by["Nickname"], "Sam")
    apply_field(page, by["Town in frame"], "Salem")
    apply_field(page, by["Your vehicles"], [{"Make": "Honda", "Colour": "Red"}, {"Make": "Ford", "Colour": "Blue"}])
    after = {f.label: f for f in inspect_form(page).fields}
    got = {k: after[k].value for k in ("Month", "Year", "Hay fever", "Nickname", "Town in frame", "Your vehicles")}
    print(got)
    assert got == {"Month": "March", "Year": "2020", "Hay fever": "No", "Nickname": "Sam", "Town in frame": "Salem",
                   "Your vehicles": [["Honda", "Red"], ["Ford", "Blue"]]}
    assert not page.evaluate("() => window.submitted")
    browser.close()
server.shutdown()
print("widgets ok")
