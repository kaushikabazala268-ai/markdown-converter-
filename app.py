import streamlit as st
import pdfplumber
import tempfile
import os
import re

# Set up page configuration
st.set_page_config(
    page_title="Universal Markdown Schema Matcher",
    page_icon="📄",
    layout="wide"
)

st.title("📄 Universal Markdown Schema Matcher & Side-by-Side Viewer")
st.write("Upload any two files (Word or PDF) to convert them with identical formatting and layout logic.")

def clean_and_normalize_text(text):
    """Standardizes spaces and removes duplicate structural line breaks"""
    if not text:
        return ""
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def process_pdf_strictly(file_path):
    """Extracts PDF layout page-by-page, keeping tables locked directly within text blocks"""
    markdown_lines = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text(layout=True)
            tables = page.extract_tables()
            
            if page_text:
                cleaned_text = clean_and_normalize_text(page_text)
                markdown_lines.append(cleaned_text)
                
            for table in tables:
                if not table or len(table) == 0:
                    continue
                markdown_lines.append("\n")
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
    """Safely extracts text and tables sequentially from Word files using standard module fallbacks"""
    # Direct try-except import handles cached server package paths dynamically
    try:
        import docx
    except ModuleNotFoundError:
        # Fallback inline installer if server cache is stubborn
        os.system("pip install python-docx")
        import docx
        
    doc = docx.Document(file_path)
    markdown_lines = []
    body = doc.element.body
    
    for child in body.iterchildren():
        if child.tag.endswith('p'):
            from docx.text.paragraph import Paragraph
            p = Paragraph(child, doc)
            if p.text.strip():
                markdown_lines.append(clean_and_normalize_text(p.text))
                
        elif child.tag.endswith('tbl'):
            from docx.table import Table
            t = Table(child, doc)
            if not t.rows or len(t.rows) == 0:
                continue
                
            markdown_lines.append("\n")
            grid_matrix = []
            
            # Loop through each row and extract cells explicitly without duplicating cells
            for row in t.rows:
                row_cells = []
                for cell in row.cells:
                    cell_text = cell.text.replace('\n', ' ').strip()
                    # Word sometimes repeats text on merged grid cells; this keeps text clean
                    if not row_cells or row_cells[-1] != cell_text:
                        row_cells.append(cell_text)
                if row_cells:
                    grid_matrix.append(row_cells)
            
            if grid_matrix:
                max_cols = max(len(r) for r in grid_matrix)
                # Pad shorter rows to ensure clean table alignment grids
                for r in grid_matrix:
                    while len(r) < max_cols:
                        r.append("")
                        
                header = "| " + " | ".join(grid_matrix[0]) + " |"
                separator = "| " + " | ".join(["---"] * max_cols) + " |"
                markdown_lines.append(header)
                markdown_lines.append(separator)
                
                for row_data in grid_matrix[1:]:
                    row_text = "| " + " | ".join(row_data) + " |"
                    markdown_lines.append(row_text)
                    
            markdown_lines.append("\n")
            
    return "\n\n".join(markdown_lines)

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
                    value=converted_markdowns[0],  # Explicitly isolates ONLY Document 1 text string
                    height=600,
                    key="side_view_doc1",
                    label_visibility="collapsed"
                )
                
            with diff_cols[1]:
                st.markdown(f"**Right: {uploaded_files[1].name}**")
                st.text_area(
                    label="Doc 2 Output View",
                    value=converted_markdowns[1],  # Explicitly isolates ONLY Document 2 text string
                    height=600,
                    key="side_view_doc2",
                    label_visibility="collapsed"
                )
