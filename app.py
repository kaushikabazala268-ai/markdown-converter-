"""
Document Diff Analyzer
======================
Upload two PDF or DOCX files → both are converted to Markdown → a
line-level diff with word-level highlighting is shown inline and
available as a downloadable HTML report.
"""

import difflib
import os
import re
from collections import defaultdict
from datetime import datetime

import docx
from docx.oxml.ns import qn
import pdfplumber
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Document Diff Analyzer",
    page_icon="🔍",
    layout="wide",
)

# ─────────────────────────────────────────────────────────────────────────────
# Shared CSS injected once
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* ── global ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* ── diff viewer ── */
    .diff-wrap {
        font-family: 'JetBrains Mono', monospace;
        font-size: 13px;
        line-height: 1.65;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        overflow-x: auto;
        background: #ffffff;
    }
    .diff-table { width: 100%; border-collapse: collapse; }
    .diff-table td { padding: 2px 12px; vertical-align: top; white-space: pre-wrap; word-break: break-word; }
    .diff-table td.ln {
        width: 38px; min-width: 38px; text-align: right;
        color: #94a3b8; user-select: none; border-right: 1px solid #e2e8f0;
        padding-right: 8px; font-size: 11px;
    }
    .diff-table tr.eq  td.code { background: #ffffff; }
    .diff-table tr.del td.code { background: #fff1f2; }
    .diff-table tr.ins td.code { background: #f0fdf4; }
    .diff-table tr.del td.ln   { background: #ffe4e6; }
    .diff-table tr.ins td.ln   { background: #dcfce7; }

    /* word-level chips */
    .wd { border-radius: 3px; padding: 1px 0; }
    .wd-del { background: #fca5a5; color: #7f1d1d; text-decoration: line-through; }
    .wd-ins { background: #86efac; color: #14532d; }

    /* ── legend ── */
    .legend { display:flex; gap:18px; padding: 10px 16px; font-size:13px;
              border-bottom: 1px solid #e2e8f0; flex-wrap: wrap; }
    .leg-item { display:flex; align-items:center; gap:6px; }
    .leg-sq { width:14px; height:14px; border-radius:3px; flex-shrink:0; }

    /* ── stat badges ── */
    .stat-row { display:flex; gap:12px; flex-wrap:wrap; margin-bottom:14px; }
    .stat-badge {
        display:inline-flex; align-items:center; gap:6px;
        padding: 5px 12px; border-radius:20px; font-size:13px; font-weight:500;
    }
    .badge-del { background:#fee2e2; color:#991b1b; }
    .badge-ins { background:#dcfce7; color:#166534; }
    .badge-mod { background:#fef3c7; color:#92400e; }
    .badge-eq  { background:#f1f5f9; color:#475569; }

    /* ── section header ── */
    .section-hdr {
        font-size: 17px; font-weight: 600; color: #1e293b;
        margin: 22px 0 10px; letter-spacing: -0.02em;
    }

    /* ── upload zone ── */
    div[data-testid="stFileUploader"] { border-radius: 10px; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────────────────────────────────────
# Extraction helpers
# ─────────────────────────────────────────────────────────────────────────────

def _table_to_md(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    lines = []
    header = [str(c or "").strip() for c in rows[0]]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")
    for row in rows[1:]:
        cells = [str(c or "").strip() for c in row]
        while len(cells) < len(header):
            cells.append("")
        lines.append("| " + " | ".join(cells[: len(header)]) + " |")
    return "\n".join(lines)


def _normalize(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pdf(uploaded_file) -> str:
    blocks: list[tuple[str, str]] = []  # (kind, content)
    PARA_GAP = 14  # pts

    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            words = page.extract_words(x_tolerance=3, y_tolerance=3, use_text_flow=True)

            line_map: dict[int, list[str]] = defaultdict(list)
            for w in words:
                line_map[round(w["top"])].append(w["text"])
            text_lines = [(y, " ".join(ws)) for y, ws in sorted(line_map.items())]

            tbl_settings = {"vertical_strategy": "lines", "horizontal_strategy": "lines"}
            table_regions: list[tuple[float, float, str]] = []
            for t in page.find_tables(tbl_settings):
                data = t.extract()
                if data:
                    table_regions.append((t.bbox[1], t.bbox[3], _table_to_md(data)))

            def inside_table(y: float) -> bool:
                return any(tb <= y <= bb for tb, bb, _ in table_regions)

            cur_y: list[float] = []
            cur_txt: list[str] = []
            pending: list[tuple[float, str, str]] = []

            def flush_text():
                if cur_txt:
                    avg = sum(cur_y) / len(cur_y)
                    pending.append((avg, "text", " ".join(cur_txt).strip()))
                    cur_y.clear(); cur_txt.clear()

            for y, line in text_lines:
                if inside_table(y):
                    flush_text(); continue
                if cur_y and (y - cur_y[-1]) > PARA_GAP:
                    flush_text()
                cur_y.append(y); cur_txt.append(line)
            flush_text()

            for tb, bb, md in table_regions:
                pending.append((tb, "table", md))

            pending.sort(key=lambda x: x[0])
            for _, kind, content in pending:
                blocks.append((kind, content))

    out: list[str] = []
    prev = None
    for kind, content in blocks:
        if kind == "text":
            if prev == "text":
                out.append("")
            out.append(content)
        else:
            out.append(content)
        prev = kind

    return _normalize("\n".join(out))


def extract_docx(uploaded_file) -> str:
    doc = docx.Document(uploaded_file)
    body = doc.element.body
    out: list[str] = []
    prev = None

    for child in body.iterchildren():
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag

        if tag == "p":
            text = "".join(r.text or "" for r in child.iter(qn("w:t"))).strip()
            if not text:
                continue
            if prev == "text":
                out.append("")
            out.append(text)
            prev = "text"

        elif tag == "tbl":
            rows = []
            for tr in child.iter(qn("w:tr")):
                cells = [
                    "".join(r.text or "" for r in tc.iter(qn("w:t"))).strip()
                    for tc in tr.iter(qn("w:tc"))
                ]
                if cells:
                    rows.append(cells)
            if rows:
                out.append(_table_to_md(rows))
                prev = "table"

    return _normalize("\n".join(out))


def extract(uploaded_file) -> str:
    ext = uploaded_file.name.rsplit(".", 1)[-1].lower()
    if ext == "pdf":
        return extract_pdf(uploaded_file)
    return extract_docx(uploaded_file)


# ─────────────────────────────────────────────────────────────────────────────
# Diff engine
# ─────────────────────────────────────────────────────────────────────────────

def word_diff_html(old_line: str, new_line: str) -> tuple[str, str]:
    """Return (left_html, right_html) with word-level <span> highlights."""
    ow = old_line.split()
    nw = new_line.split()
    sm = difflib.SequenceMatcher(None, ow, nw, autojunk=False)

    left_parts, right_parts = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            chunk = " ".join(ow[i1:i2])
            left_parts.append(chunk)
            right_parts.append(chunk)
        elif tag == "replace":
            left_parts.append(
                f'<span class="wd wd-del">{" ".join(ow[i1:i2])}</span>'
            )
            right_parts.append(
                f'<span class="wd wd-ins">{" ".join(nw[j1:j2])}</span>'
            )
        elif tag == "delete":
            left_parts.append(
                f'<span class="wd wd-del">{" ".join(ow[i1:i2])}</span>'
            )
        elif tag == "insert":
            right_parts.append(
                f'<span class="wd wd-ins">{" ".join(nw[j1:j2])}</span>'
            )

    return " ".join(left_parts), " ".join(right_parts)


def build_diff(lines_a: list[str], lines_b: list[str]) -> list[dict]:
    """
    Return a list of row dicts:
      { type: 'equal'|'delete'|'insert'|'replace',
        ln_a: int|None, ln_b: int|None,
        left: str, right: str }   (left/right are HTML-safe strings)
    """
    sm = difflib.SequenceMatcher(None, lines_a, lines_b, autojunk=False)
    rows = []
    a_ctr = b_ctr = 1

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                escaped = _esc(lines_a[i1 + k])
                rows.append(
                    dict(type="equal", ln_a=a_ctr, ln_b=b_ctr, left=escaped, right=escaped)
                )
                a_ctr += 1; b_ctr += 1

        elif tag == "replace":
            # Pair up lines; unmatched get empty partner
            block_a = lines_a[i1:i2]
            block_b = lines_b[j1:j2]
            n = max(len(block_a), len(block_b))
            for k in range(n):
                la = block_a[k] if k < len(block_a) else ""
                lb = block_b[k] if k < len(block_b) else ""
                lh, rh = word_diff_html(_esc(la), _esc(lb))
                rows.append(
                    dict(
                        type="replace",
                        ln_a=a_ctr if k < len(block_a) else None,
                        ln_b=b_ctr if k < len(block_b) else None,
                        left=lh, right=rh,
                    )
                )
                if k < len(block_a): a_ctr += 1
                if k < len(block_b): b_ctr += 1

        elif tag == "delete":
            for k in range(i2 - i1):
                rows.append(
                    dict(type="delete", ln_a=a_ctr, ln_b=None,
                         left=_esc(lines_a[i1 + k]), right="")
                )
                a_ctr += 1

        elif tag == "insert":
            for k in range(j2 - j1):
                rows.append(
                    dict(type="insert", ln_a=None, ln_b=b_ctr,
                         left="", right=_esc(lines_b[j1 + k]))
                )
                b_ctr += 1

    return rows


def _esc(s: str) -> str:
    """HTML-escape but preserve already-injected <span> tags from word_diff."""
    # Only escape raw strings (no spans yet)
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
    )


# ─────────────────────────────────────────────────────────────────────────────
# Render helpers
# ─────────────────────────────────────────────────────────────────────────────

CSS_CLASS = {"equal": "eq", "delete": "del", "insert": "ins", "replace": "mod"}


def rows_to_html_table(rows: list[dict], left_label: str, right_label: str) -> str:
    """Render diff rows as a side-by-side HTML table."""
    thead = (
        f"<thead><tr>"
        f"<td class='ln'></td><td class='code' style='font-weight:600;color:#334155;"
        f"border-bottom:2px solid #e2e8f0;padding-bottom:6px'>{_esc(left_label)}</td>"
        f"<td class='ln'></td><td class='code' style='font-weight:600;color:#334155;"
        f"border-bottom:2px solid #e2e8f0;padding-bottom:6px'>{_esc(right_label)}</td>"
        f"</tr></thead>"
    )
    body_rows = []
    for r in rows:
        cls = CSS_CLASS[r["type"]]
        ln_a = r["ln_a"] if r["ln_a"] is not None else ""
        ln_b = r["ln_b"] if r["ln_b"] is not None else ""
        # For delete rows right cell gets eq background; for insert left gets eq
        right_cls = "del" if r["type"] == "delete" else cls
        left_cls  = "ins" if r["type"] == "insert"  else cls
        body_rows.append(
            f"<tr class='{cls}'>"
            f"<td class='ln {left_cls}'>{ln_a}</td>"
            f"<td class='code'>{r['left']}</td>"
            f"<td class='ln {right_cls}'>{ln_b}</td>"
            f"<td class='code'>{r['right']}</td>"
            f"</tr>"
        )
    return f"<table class='diff-table'>{thead}<tbody>{''.join(body_rows)}</tbody></table>"


def stats_html(rows: list[dict]) -> tuple[str, dict]:
    counts = defaultdict(int)
    for r in rows:
        counts[r["type"]] += 1
    total = len(rows)
    s = counts
    html = (
        f"<div class='stat-row'>"
        f"<span class='stat-badge badge-del'>🗑 {s['delete']} deleted</span>"
        f"<span class='stat-badge badge-ins'>✚ {s['insert']} added</span>"
        f"<span class='stat-badge badge-mod'>✎ {s['replace']} modified</span>"
        f"<span class='stat-badge badge-eq'>= {s['equal']} unchanged</span>"
        f"</div>"
    )
    return html, dict(s)


LEGEND_HTML = """
<div class='legend'>
  <div class='leg-item'><div class='leg-sq' style='background:#fee2e2'></div>Deleted line</div>
  <div class='leg-item'><div class='leg-sq' style='background:#dcfce7'></div>Added line</div>
  <div class='leg-item'><div class='leg-sq' style='background:#fca5a5'></div>
    <span class='wd wd-del' style='border-radius:3px;padding:1px 4px'>removed words</span></div>
  <div class='leg-item'><div class='leg-sq' style='background:#86efac'></div>
    <span class='wd wd-ins' style='border-radius:3px;padding:1px 4px'>added words</span></div>
</div>
"""


def build_full_html_report(
    left_label: str, right_label: str,
    stats_h: str, table_html: str,
    md_a: str, md_b: str,
) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Diff Report – {_esc(left_label)} vs {_esc(right_label)}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Inter',sans-serif;background:#f8fafc;color:#1e293b;padding:32px 24px}}
h1{{font-size:22px;font-weight:600;letter-spacing:-0.03em;margin-bottom:4px}}
.subtitle{{font-size:13px;color:#64748b;margin-bottom:24px}}
.section-hdr{{font-size:17px;font-weight:600;color:#1e293b;margin:28px 0 10px;letter-spacing:-0.02em}}
.stat-row{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px}}
.stat-badge{{display:inline-flex;align-items:center;gap:6px;padding:5px 12px;border-radius:20px;font-size:13px;font-weight:500}}
.badge-del{{background:#fee2e2;color:#991b1b}}
.badge-ins{{background:#dcfce7;color:#166534}}
.badge-mod{{background:#fef3c7;color:#92400e}}
.badge-eq{{background:#f1f5f9;color:#475569}}
.legend{{display:flex;gap:18px;padding:10px 16px;font-size:13px;border-bottom:1px solid #e2e8f0;flex-wrap:wrap}}
.leg-item{{display:flex;align-items:center;gap:6px}}
.leg-sq{{width:14px;height:14px;border-radius:3px;flex-shrink:0}}
.diff-wrap{{font-family:'JetBrains Mono',monospace;font-size:13px;line-height:1.65;border:1px solid #e2e8f0;border-radius:10px;overflow-x:auto;background:#fff;margin-bottom:32px}}
.diff-table{{width:100%;border-collapse:collapse}}
.diff-table td{{padding:2px 12px;vertical-align:top;white-space:pre-wrap;word-break:break-word}}
.diff-table td.ln{{width:38px;min-width:38px;text-align:right;color:#94a3b8;user-select:none;border-right:1px solid #e2e8f0;padding-right:8px;font-size:11px}}
.diff-table tr.eq  td.code{{background:#fff}}
.diff-table tr.del td.code{{background:#fff1f2}}
.diff-table tr.ins td.code{{background:#f0fdf4}}
.diff-table tr.del td.ln{{background:#ffe4e6}}
.diff-table tr.ins td.ln{{background:#dcfce7}}
.wd{{border-radius:3px;padding:1px 0}}
.wd-del{{background:#fca5a5;color:#7f1d1d;text-decoration:line-through}}
.wd-ins{{background:#86efac;color:#14532d}}
.md-block{{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:16px 20px;font-family:'JetBrains Mono',monospace;font-size:12px;white-space:pre-wrap;word-break:break-word;max-height:400px;overflow-y:auto;margin-bottom:16px}}
</style>
</head>
<body>
<h1>🔍 Document Diff Report</h1>
<div class="subtitle">Generated {ts} &nbsp;·&nbsp; <strong>{_esc(left_label)}</strong> vs <strong>{_esc(right_label)}</strong></div>

<div class="section-hdr">Summary</div>
{stats_h}

<div class="section-hdr">Line-by-Line Diff (word-level highlights)</div>
<div class="diff-wrap">
{LEGEND_HTML}
{table_html}
</div>

<div class="section-hdr">Extracted Markdown – {_esc(left_label)}</div>
<div class="md-block">{_esc(md_a)}</div>

<div class="section-hdr">Extracted Markdown – {_esc(right_label)}</div>
<div class="md-block">{_esc(md_b)}</div>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
# App UI
# ─────────────────────────────────────────────────────────────────────────────

st.markdown(
    "<h1 style='font-size:26px;font-weight:700;letter-spacing:-0.03em;margin-bottom:4px'>"
    "🔍 Document Diff Analyzer</h1>"
    "<p style='color:#64748b;font-size:14px;margin-bottom:24px'>"
    "Upload two PDF or DOCX files — both are converted to Markdown, "
    "then compared line-by-line with word-level highlighting.</p>",
    unsafe_allow_html=True,
)

col_up1, col_up2 = st.columns(2)
with col_up1:
    file_a = st.file_uploader("📄 Original document", type=["pdf", "docx"], key="file_a")
with col_up2:
    file_b = st.file_uploader("📄 Revised document", type=["pdf", "docx"], key="file_b")

if not file_a or not file_b:
    st.info("Upload both documents above to start the comparison.")
    st.stop()

# ── Extract ───────────────────────────────────────────────────────────────────
with st.spinner("Extracting and converting documents…"):
    try:
        md_a = extract(file_a)
        md_b = extract(file_b)
    except Exception as e:
        st.error(f"Extraction failed: {e}")
        st.stop()

label_a = file_a.name
label_b = file_b.name

# ── Markdown downloads ────────────────────────────────────────────────────────
with st.expander("📋 View / download extracted Markdown", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**{label_a}**")
        st.text_area("md_a", md_a, height=260, label_visibility="collapsed", key="ta_a")
        st.download_button(
            "📥 Download Markdown A", md_a,
            file_name=label_a.rsplit(".", 1)[0] + ".md",
            mime="text/markdown", key="dl_a",
        )
    with c2:
        st.markdown(f"**{label_b}**")
        st.text_area("md_b", md_b, height=260, label_visibility="collapsed", key="ta_b")
        st.download_button(
            "📥 Download Markdown B", md_b,
            file_name=label_b.rsplit(".", 1)[0] + ".md",
            mime="text/markdown", key="dl_b",
        )

# ── Diff ──────────────────────────────────────────────────────────────────────
lines_a = md_a.splitlines()
lines_b = md_b.splitlines()

with st.spinner("Computing diff…"):
    diff_rows = build_diff(lines_a, lines_b)

stats_h, counts = stats_html(diff_rows)
table_html = rows_to_html_table(diff_rows, label_a, label_b)

# ── Stats ─────────────────────────────────────────────────────────────────────
st.markdown("<div class='section-hdr'>Summary</div>", unsafe_allow_html=True)
st.markdown(stats_h, unsafe_allow_html=True)

# ── Filter toggle ─────────────────────────────────────────────────────────────
show_unchanged = st.checkbox("Show unchanged lines", value=True)
if not show_unchanged:
    visible = [r for r in diff_rows if r["type"] != "equal"]
    if not visible:
        st.success("✅ No differences found — the documents are identical.")
        st.stop()
    table_html_filtered = rows_to_html_table(visible, label_a, label_b)
else:
    table_html_filtered = table_html

# ── Inline diff viewer ────────────────────────────────────────────────────────
st.markdown("<div class='section-hdr'>Line-by-Line Diff</div>", unsafe_allow_html=True)
st.markdown(LEGEND_HTML, unsafe_allow_html=True)

st.markdown(
    f"<div class='diff-wrap'>{table_html_filtered}</div>",
    unsafe_allow_html=True,
)

# ── Downloadable HTML report ──────────────────────────────────────────────────
report_html = build_full_html_report(
    label_a, label_b, stats_h, table_html, md_a, md_b
)

st.markdown("---")
st.download_button(
    label="📥 Download full diff report (HTML)",
    data=report_html,
    file_name="diff_report.html",
    mime="text/html",
    use_container_width=True,
)
