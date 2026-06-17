import streamlit as st
from docling.document_converter import DocumentConverter, PdfFormatOption, WordFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat
from docling_core.types.doc import DocItemLabel, TableItem
import tempfile
import re
import os
import gc

st.set_page_config(
    page_title="Universal Markdown Schema Matcher",
    page_icon="📄",
    layout="wide"
)

st.title("📄 Universal Markdown Schema Matcher & Side-by-Side Viewer")
st.write("Upload any two files (Word or PDF) to convert them with strict layout order and compare them side by side.")

@st.cache_resource
def get_unified_converter():
    pdf_options = PdfPipelineOptions()
    pdf_options.do_ocr = False
    pdf_options.do_table_structure = True 
    
    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options),
            InputFormat.DOCX: WordFormatOption()
        }
    )

converter = get_unified_converter()

def clean_spacing(text):
    """Fixes inconsistent spaces, removes duplicate line-breaks, and preserves inline numbering"""
    if not text:
        return ""
    # Normalize irregular spaces into single spaces
    text = re.sub(r'[ \t]+', ' ', text)
    # Ensure nested line items or section breaks have standard spacing
    return text.strip()

def compile_strict_layout_markdown(conversion_result):
    """Assembles elements chronologically from the document tree map to prevent table shifting"""
    doc = conversion_result.document
    markdown_lines = []
    
    # Walk through every structural item sequentially as it appears in the file tree
    for item, _ in doc.iterate_items():
        # Handle Tables immediately in their chronological position
        if isinstance(item, TableItem) or item.label == DocItemLabel.TABLE:
            try:
                # Convert the table matrix to standard markdown grid
                markdown_lines.append("\n" + item.export_to_markdown() + "\n")
            except Exception:
                # Fallback if standard element export fails
                grid_data = getattr(item, 'data', None)
                if grid_data and hasattr(grid_data, 'table_cells'):
                    markdown_lines.append("\n<!-- Table Fallback -->\n")
            continue
            
        # Handle Headings and Titles
        if item.label in [DocItemLabel.TITLE, DocItemLabel.SECTION_HEADER, DocItemLabel.HEADING]:
            text_content = clean_spacing(getattr(item, 'text', ''))
            if text_content:
                markdown_lines.append(f"\n## {text_content}\n")
                
        # Handle regular Paragraph text and List Items safely preserving numbering prefixes
        elif item.label in [DocItemLabel.TEXT, DocItemLabel.PARAGRAPH, DocItemLabel.LIST_ITEM]:
            text_content = clean_spacing(getattr(item, 'text', ''))
            if text_content:
                # Check if it already contains numbering (e.g. 2.1, 2.2) to prevent stripping
                if re.match(r'^[\d\.\-]+\s', text_content):
                    markdown_lines.append(text_content)
                else:
                    markdown_lines.append(text_content)
                    
    # Join with clean line spacing intervals
    full_md = "\n\n".join([line for line in markdown_lines if line])
    # Final cleanup of multiple excessive empty newlines
    return re.sub(r'\n{3,}', '\n\n', full_md)

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
        # Create columns to report individual loading status
        status_cols = st.columns(len(uploaded_files))
        
        for idx, uploaded_file in enumerate(uploaded_files):
            with status_cols[idx]:
                with st.spinner(f"Processing {uploaded_file.name}..."):
                    try:
                        suffix = f".{uploaded_file.name.split('.')[-1]}".lower()
                        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                            temp_file.write(uploaded_file.getvalue())
                            temp_file_path = temp_file.name

                        result = converter.convert(temp_file_path)
                        
                        # Generate the strict chronological markdown array
                        markdown_output = compile_strict_layout_markdown(result)
                        converted_markdowns[idx] = markdown_output
                        
                        os.remove(temp_file_path)
                        gc.collect()
                        
                        st.success(f"📄 Doc {idx+1} Loaded")
                        
                        base_name, _ = os.path.splitext(uploaded_file.name)
                        st.download_button(
                            label=f"📥 Download Markdown {idx+1}",
                            data=markdown_output,
                            file_name=f"{base_name}.md",
                            mime="text/markdown",
                            key=f"dl_btn_{idx}"
                        )
                        
                    except Exception as e:
                        st.error(f"Error parsing file: {e}")
                        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                            os.remove(temp_file_path)
                        gc.collect()

        # --- TRUE SIDE-BY-SIDE DISPLAY ---
        if len(uploaded_files) == 2 and 0 in converted_markdowns and 1 in converted_markdowns:
            st.markdown("---")
            st.header("🔍 Side-by-Side Content View")
            
            diff_cols = st.columns(2)
            
            with diff_cols[0]:
                st.markdown(f"**Left: {uploaded_files[0].name}**")
                st.text_area(
                    label="Doc 1",
                    value=converted_markdowns[0], # Explicitly targets only Document 1
                    height=600,
                    key="side_view_doc1",
                    label_visibility="collapsed"
                )
                
            with diff_cols[1]:
                st.markdown(f"**Right: {uploaded_files[1].name}**")
                st.text_area(
                    label="Doc 2",
                    value=converted_markdowns[1], # Explicitly targets only Document 2
                    height=600,
                    key="side_view_doc2",
                    label_visibility="collapsed"
                )
