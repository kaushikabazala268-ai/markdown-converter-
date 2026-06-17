import streamlit as st
import pdfplumber
import docx2txt
import tempfile
import os
import re

st.set_page_config(
    page_title="Universal Markdown Schema Matcher",
    page_icon="📄",
    layout="wide"
)

st.title("📄 Universal Markdown Schema Matcher & Side-by-Side Viewer")
st.write("Upload any two files (Word or PDF) to convert them with identical formatting and layout logic.")

def clean_and_normalize_text(text):
    """Fixes word document spacing gaps and standardizes markdown structural breaks"""
    if not text:
        return ""
    # Convert irregular tab gaps into standard spaces
    text = re.sub(r'[ \t]+', ' ', text)
    # Ensure any running lists retain their literal prefixes (like 2.1, 2.2) safely
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def process_pdf_strictly(file_path):
    """Extracts PDF layout page-by-page, keeping tables locked directly within text blocks"""
    markdown_lines = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            # Step 1: Extract all structural layout blocks on the page chronologically
            page_text = page.extract_text(layout=True)
            tables = page.extract_tables()
            
            if page_text:
                cleaned_text = clean_and_normalize_text(page_text)
                markdown_lines.append(cleaned_text)
                
            # Step 2: Format and append tables right under their target paragraph sections
            for table in tables:
                if not table or not table[0]:
                    continue
                markdown_lines.append("\n")
                # Construct identical Markdown grid schema
                header = "| " + " | ".join([str(cell or '').strip() for cell in table[0]]) + " |"
                separator = "| " + " | ".join(["---"] * len(table[0])) + " |"
                markdown_lines.append(header)
                markdown_lines.append(separator)
                for row in table[1:]:
                    row_text = "| " + " | ".join([str(cell or '').strip() for cell in row]) + " |"
                    markdown_lines.append(row_text)
                markdown_lines.append("\n")
                
    return "\n\n".join(markdown_lines)

def process_docx_strictly(file_path):
    """Processes Word document xml segments into an identical text layout pattern"""
    raw_text = docx2txt.process(file_path)
    return clean_and_normalize_text(raw_text)

uploaded_files = st.file_uploader(
    "Upload exactly two documents to compare (PDF or DOCX)", 
    type=["pdf", "docx"],
    accept_multiple_files=True
)

converted_markdowns = {}

if uploaded_files:
    if len(uploaded_files) > 2:
        st.error("⚠️ Maximum of two files allowed for comparison.")
    else:
        status_cols = st.columns(len(uploaded_files))
        
        for idx, uploaded_file in enumerate(uploaded_files):
            with status_cols[idx]:
                with st.spinner(f"Converting {uploaded_file.name}..."):
                    try:
                        suffix = f".{uploaded_file.name.split('.')[-1]}".lower()
                        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                            temp_file.write(uploaded_file.getvalue())
                            temp_file_path = temp_file.name

                        # Routing parsing execution pathways safely based on extension types
                        if suffix == ".pdf":
                            output = process_pdf_strictly(temp_file_path)
                        else:
                            output = process_docx_strictly(temp_file_path)
                            
                        converted_markdowns[idx] = output
                        os.remove(temp_file_path)
                        
                        st.success(f"📄 Doc {idx+1} Loaded")
                        
                        base_name, _ = os.path.splitext(uploaded_file.name)
                        st.download_button(
                            label=f"📥 Download Markdown {idx+1}",
                            data=output,
                            file_name=f"{base_name}.md",
                            mime="text/markdown",
                            key=f"dl_btn_{idx}"
                        )
                        
                    except Exception as e:
                        st.error(f"Error parsing file: {e}")
                        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                            os.remove(temp_file_path)

        # --- TRUE SIDE-BY-SIDE SEPARATED INTERFACE ---
        if len(uploaded_files) == 2 and 0 in converted_markdowns and 1 in converted_markdowns:
            st.markdown("---")
            st.header("🔍 Side-by-Side Content View")
            
            diff_cols = st.columns(2)
            
            with diff_cols[0]:
                st.markdown(f"**Left: {uploaded_files[0].name}**")
                st.text_area(
                    label="Doc 1 Output View",
                    value=converted_markdowns[0],  # Correctly isolates Document 1 text string
                    height=600,
                    key="side_view_doc1",
                    label_visibility="collapsed"
                )
                
            with diff_cols[1]:
                st.markdown(f"**Right: {uploaded_files[1].name}**")
                st.text_area(
                    label="Doc 2 Output View",
                    value=converted_markdowns[1],  # Correctly isolates Document 2 text string
                    height=600,
                    key="side_view_doc2",
                    label_visibility="collapsed"
                )
