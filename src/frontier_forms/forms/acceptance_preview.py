"""CSS-styled successor preview endpoint, leaving frozen /forms HTML unchanged."""
from .templates import render_html

PREVIEW_CSS = """
body{font:15px Helvetica,Arial,sans-serif;max-width:860px;margin:28px auto;padding:0 16px;background:#fafafa;color:#15202b}
h1{font-size:23px}
.banner{font-size:12px;border:1px solid #d5dadf;padding:10px;border-radius:6px}
.row{margin:12px 0;break-inside:avoid}
label{display:block;font-weight:550;margin-bottom:4px}
input,textarea,select{box-sizing:border-box;width:100%;font-size:15px;padding:8px;min-height:40px;border:1px solid #9ea9b5;border-radius:5px;background:white}
textarea{min-height:92px}
button{padding:10px 16px;background:#183e66;color:white;border:0;border-radius:5px}
@media print{body{background:white;color:black;width:auto}.row{break-inside:avoid}button{display:none}}
"""

def render_preview_html(template):
    """Versioned CSS preview; does NOT expose canonical_key or answer oracle."""
    html=render_html(template)
    assert "<head>" in html
    return html.replace("<head>", "<head><style>" + PREVIEW_CSS + "</style>", 1)
