import streamlit as st
from docling.document_converter import DocumentConverter, PdfFormatOption, WordFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat
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
st.write("Upload any two files (Word or PDF) to convert them with identical formatting and layout logic.")

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

def unify_and_clean_markdown(raw_markdown):
    """Normalizes whitespace and formats both Word and PDF into an identical schema"""
    if not raw_markdown:
        return ""
    
    # Replace tab spaces or irregular text gaps with a standard single space
    text = re.sub(r'[ \t]+', ' ', raw_markdown)
    
    # Ensure all tables have a clean newline cushion around them so they render correctly
    text = re.sub(r'(\|.*\|)\n([^|])', r'\1\n\n\2', text)
    
    # Eliminate multiple redundant empty lines down to a clean double newline spacing
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
        st.error("⚠️ Maximum of two files allowed for comparison.")
    else:
        # Step 1: Sequential data loading and processing status
        status_cols = st.columns(len(uploaded_files))
        
        for idx, uploaded_file in enumerate(uploaded_files):
            with status_cols[idx]:
                with st.spinner(f"Converting {uploaded_file.name}..."):
                    try:
                        suffix = f".{uploaded_file.name.split('.')[-1]}".lower()
                        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                            temp_file.write(uploaded_file.getvalue())
                            temp_file_path = temp_file.name

                        # Run core conversion engine
                        result = converter.convert(temp_file_path)
                        raw_output = result.document.export_to_markdown()
                        
                        # Apply our text mapping filter for equal formats
                        markdown_output = unify_and_clean_markdown(raw_output)
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

        # --- STEP 2: TRUE SIDE-BY-SIDE SEPARATED INTERFACE ---
        if len(uploaded_files) == 2 and 0 in converted_markdowns and 1 in converted_markdowns:
            st.markdown("---")
            st.header("🔍 Side-by-Side Content View")
            
            diff_cols = st.columns(2)
            
            with diff_cols[0]:
                st.markdown(f"**Left: {uploaded_files[0].name}**")
                st.text_area(
                    label="Doc 1 Output View",
                    value=converted_markdowns[0],  # Isolates ONLY document index 0 data stream
                    height=600,
                    key="side_view_doc1",
                    label_visibility="collapsed"
                )
                
            with diff_cols[1]:
                st.markdown(f"**Right: {uploaded_files[1].name}**")
                st.text_area(
                    label="Doc 2 Output View",
                    value=converted_markdowns[1],  # Isolates ONLY document index 1 data stream
                    height=600,
                    key="side_view_doc2",
                    label_visibility="collapsed"
                )
