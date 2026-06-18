import streamlit as st
import pdfplumber
import docx
from docx.oxml.ns import qn
import os
import re

st.set_page_config(
    page_title="Universal Markdown Schema Matcher",
    page_icon="📄",
    layout="wide"
)

st.title("📄 Universal Markdown Schema Matcher")
st.write("Convert PDFs and Word docs into mathematically identical layouts with strict table mapping.")


def normalize_markdown_format(text):
    """Collapse runs of 3+ blank lines to max 1 blank line between blocks."""
    if not text:
        return ""
    # Collapse horizontal whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    # Replace 3 or more newlines with exactly 2 (one blank line)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def table_to_md(rows):
    """Convert a 2-D list of strings into a Markdown table string."""
    if not rows:
        return ""
    lines = []
    header = [str(c or '').strip() for c in rows[0]]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")
    for row in rows[1:]:
        cells = [str(c or '').strip() for c in row]
        # Pad / trim to match header width
        while len(cells) < len(header):
            cells.append("")
        lines.append("| " + " | ".join(cells[:len(header)]) + " |")
    return "\n".join(lines)


def extract_pdf(uploaded_file):
    """
    Extract text from a PDF preserving the reading order of paragraphs and
    tables.  Tables are inserted immediately after the paragraph that ends
    just above them (no extra blank line inserted between them).
    """
    blocks = []   # list of (top_y, kind, content)

    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            page_height = page.height

            # ── collect text lines via words ──────────────────────────────
            words = page.extract_words(
                x_tolerance=3, y_tolerance=3,
                keep_blank_chars=False,
                use_text_flow=True
            )
            # Group words into lines by rounded top-y
            from collections import defaultdict
            line_map = defaultdict(list)
            for w in words:
                key = round(w["top"])
                line_map[key].append(w["text"])
            text_lines = [(y, " ".join(ws)) for y, ws in sorted(line_map.items())]

            # ── collect tables ────────────────────────────────────────────
            table_settings = {"vertical_strategy": "lines", "horizontal_strategy": "lines"}
            tables_on_page = page.find_tables(table_settings)

            table_regions = []   # (top_y, bottom_y, md_string)
            for t in tables_on_page:
                data = t.extract()
                if data:
                    md = table_to_md(data)
                    table_regions.append((t.bbox[1], t.bbox[3], md))

            # ── merge: for each text line decide whether it falls inside a
            #    table bbox; if not, emit it as a paragraph fragment.
            #    After all lines are processed, stitch adjacent text lines
            #    into paragraphs (blank-line separated when the y-gap is large).
            PARA_GAP_THRESHOLD = 14   # pts – tune if needed

            def inside_table(y):
                for (tb, bb, _) in table_regions:
                    if tb <= y <= bb:
                        return True
                return False

            para_lines = []   # accumulator for current paragraph
            prev_y = None

            def flush_para():
                if para_lines:
                    joined = " ".join(para_lines).strip()
                    if joined:
                        y_key = round(para_lines[0] if isinstance(para_lines[0], float) else 0)
                        blocks.append(joined)
                    para_lines.clear()

            # We'll do a simpler two-pass approach:
            # Pass 1 – collect non-table text lines into paragraphs
            pending_text_blocks = []   # list of (avg_top, text)
            current_lines_y = []
            current_lines_text = []

            for (y, line_text) in text_lines:
                if inside_table(y):
                    # flush any pending paragraph first
                    if current_lines_text:
                        avg_y = sum(current_lines_y) / len(current_lines_y)
                        pending_text_blocks.append((avg_y, " ".join(current_lines_text).strip()))
                        current_lines_y.clear()
                        current_lines_text.clear()
                    continue

                if current_lines_y:
                    gap = y - current_lines_y[-1]
                    if gap > PARA_GAP_THRESHOLD:
                        # start a new paragraph
                        avg_y = sum(current_lines_y) / len(current_lines_y)
                        pending_text_blocks.append((avg_y, " ".join(current_lines_text).strip()))
                        current_lines_y.clear()
                        current_lines_text.clear()

                current_lines_y.append(y)
                current_lines_text.append(line_text)

            if current_lines_text:
                avg_y = sum(current_lines_y) / len(current_lines_y)
                pending_text_blocks.append((avg_y, " ".join(current_lines_text).strip()))

            # Pass 2 – merge text blocks and tables in y-order
            all_items = []
            for (y, txt) in pending_text_blocks:
                if txt:
                    all_items.append((y, "text", txt))
            for (tb, bb, md) in table_regions:
                all_items.append((tb, "table", md))

            all_items.sort(key=lambda x: x[0])

            for (_, kind, content) in all_items:
                blocks.append((kind, content))

    # ── render blocks to markdown ─────────────────────────────────────────
    lines_out = []
    prev_kind = None
    for (kind, content) in blocks:
        if kind == "text":
            # Add a blank line between text paragraphs, but NOT before a table
            if prev_kind == "text":
                lines_out.append("")   # one blank line = paragraph break
            lines_out.append(content)
        elif kind == "table":
            # No blank line between the preceding paragraph and its table
            lines_out.append(content)
        prev_kind = kind

    return normalize_markdown_format("\n".join(lines_out))


def extract_docx(uploaded_file):
    """
    Walk the body XML in document order so that tables immediately follow
    the paragraph that precedes them — no extra blank lines injected.
    """
    doc = docx.Document(uploaded_file)
    body = doc.element.body

    lines_out = []
    prev_kind = None   # "text" | "table"

    for child in body.iterchildren():
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag

        if tag == "p":
            # paragraph
            para_text = "".join(r.text or "" for r in child.iter(qn("w:t"))).strip()
            if not para_text:
                continue
            if prev_kind == "text":
                lines_out.append("")   # blank line between successive paragraphs
            # No blank line if previous was a table – table attaches to next para naturally
            lines_out.append(para_text)
            prev_kind = "text"

        elif tag == "tbl":
            # table – collect rows
            rows = []
            for tr in child.iter(qn("w:tr")):
                cells = []
                for tc in tr.iter(qn("w:tc")):
                    cell_text = "".join(
                        r.text or "" for r in tc.iter(qn("w:t"))
                    ).strip()
                    cells.append(cell_text)
                if cells:
                    rows.append(cells)

            if rows:
                md_table = table_to_md(rows)
                # No blank line between the preceding paragraph and its table
                lines_out.append(md_table)
                prev_kind = "table"

    return normalize_markdown_format("\n".join(lines_out))


# ── UI ────────────────────────────────────────────────────────────────────────

uploaded_files = st.file_uploader(
    "Upload exactly two documents to compare (PDF or DOCX)",
    type=["pdf", "docx"],
    accept_multiple_files=True
)

converted_markdowns = {}

if uploaded_files:
    if len(uploaded_files) > 2:
        st.error("⚠️ Maximum of two files allowed.")
    else:
        status_cols = st.columns(len(uploaded_files))

        for idx, uploaded_file in enumerate(uploaded_files):
            with status_cols[idx]:
                with st.spinner(f"Processing {uploaded_file.name}…"):
                    try:
                        suffix = uploaded_file.name.rsplit(".", 1)[-1].lower()

                        if suffix == "pdf":
                            md = extract_pdf(uploaded_file)
                        else:
                            md = extract_docx(uploaded_file)

                        converted_markdowns[idx] = md
                        st.success(f"📄 Doc {idx+1} Loaded")

                        base_name = uploaded_file.name.rsplit(".", 1)[0]
                        st.download_button(
                            label=f"📥 Download Markdown {idx+1}",
                            data=md,
                            file_name=f"{base_name}.md",
                            mime="text/markdown",
                            key=f"dl_btn_{idx}"
                        )

                    except Exception as e:
                        st.error(f"Error parsing file: {e}")

        # ── Side-by-side view ────────────────────────────────────────────
        if len(uploaded_files) == 2 and 0 in converted_markdowns and 1 in converted_markdowns:
            st.markdown("---")
            st.header("🔍 Identical Layout Side-by-Side View")

            diff_cols = st.columns(2)

            with diff_cols[0]:
                st.markdown(f"**Left Column: `{uploaded_files[0].name}`**")
                st.text_area(
                    label="Left Stream",
                    value=converted_markdowns[0],
                    height=650,
                    key="side_view_doc1",
                    label_visibility="collapsed"
                )

            with diff_cols[1]:
                st.markdown(f"**Right Column: `{uploaded_files[1].name}`**")
                st.text_area(
                    label="Right Stream",
                    value=converted_markdowns[1],
                    height=650,
                    key="side_view_doc2",
                    label_visibility="collapsed"
                )
