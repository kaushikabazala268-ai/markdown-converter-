import streamlit as st
from docling_core.types.doc import DoclingDocument
import tempfile
import json
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
    """Ensures matching spacing and keeps original numbering prefixes completely identical"""
    if not text:
        return ""
    # Remove irregular double spaces or massive tab gaps
    text = re.sub(r'[ \t]+', ' ', text)
    # Ensure uniform paragraph transitions
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

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
                with st.spinner(f"Processing structure of {uploaded_file.name}..."):
                    try:
                        # Direct fallback text extraction if server core handles streaming bytes
                        suffix = f".{uploaded_file.name.split('.')[-1]}".lower()
                        
                        if suffix == ".pdf":
                            import pdfplumber
                            with pdfplumber.open(uploaded_file) as pdf:
                                text_list = []
                                for page in pdf.pages:
                                    p_text = page.extract_text(layout=True)
                                    if p_text:
                                        text_list.append(p_text)
                                    tables = page.extract_tables()
                                    for table in tables:
                                        if table:
                                            text_list.append("\n")
                                            text_list.append("| " + " | ".join([str(c or '').strip() for c in table]) + " |")
                                            text_list.append("| " + " | ".join(["---"] * len(table)) + " |")
                                            for row in table[1:]:
                                                text_list.append("| " + " | ".join([str(c or '').strip() for c in row]) + " |")
                                            text_list.append("\n")
                                raw_md = "\n\n".join(text_list)
                        else:
                            import docx
                            doc = docx.Document(uploaded_file)
                            text_list = []
                            for p in doc.paragraphs:
                                if p.text.strip():
                                    text_list.append(p.text)
                            for table in doc.tables:
                                if table.rows:
                                    text_list.append("\n")
                                    grid = [[cell.text.strip() for cell in row.cells] for row in table.rows]
                                    text_list.append("| " + " | ".join(grid) + " |")
                                    text_list.append("| " + " | ".join(["---"] * len(grid)) + " |")
                                    for r in grid[1:]:
                                        text_list.append("| " + " | ".join(r) + " |")
                                    text_list.append("\n")
                            raw_md = "\n\n".join(text_list)
                        
                        converted_markdowns[idx] = normalize_markdown_format(raw_md)
                        st.success(f"📄 Doc {idx+1} Loaded")
                        
                        base_name, _ = os.path.splitext(uploaded_file.name)
                        st.download_button(
                            label=f"📥 Download Markdown {idx+1}",
                            data=converted_markdowns[idx],
                            file_name=f"{base_name}.md",
                            mime="text/markdown",
                            key=f"dl_btn_{idx}"
                        )
                        
                    except Exception as e:
                        st.error(f"Error parsing file: {e}")

        # --- TRUE INDEPENDENT SIDE-BY-SIDE INTERFACE DISPLAY ---
        if len(uploaded_files) == 2 and 0 in converted_markdowns and 1 in converted_markdowns:
            st.markdown("---")
            st.header("🔍 Identical Layout Side-by-Side View")
            
            diff_cols = st.columns(2)
            
            with diff_cols:
                st.markdown(f"**Left Column: `{uploaded_files.name}`**")
                st.text_area(
                    label="Left Stream",
                    value=converted_markdowns,  # CORRECT: Locks only 1st file text string here
                    height=650,
                    key="side_view_doc1",
                    label_visibility="collapsed"
                )
                
            with diff_cols:
                st.markdown(f"**Right Column: `{uploaded_files.name}`**")
                st.text_area(
                    label="Right Stream",
                    value=converted_markdowns,  # CORRECT: Locks only 2nd file text string here
                    height=650,
                    key="side_view_doc2",
                    label_visibility="collapsed"
                )
