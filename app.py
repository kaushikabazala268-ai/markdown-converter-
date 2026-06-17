import streamlit as st
import os

# Force internal deep-learning packages to use open, writable cloud folders
os.environ["HF_HOME"] = "/tmp/hf_cache"
os.environ["XDG_CACHE_HOME"] = "/tmp/xdg_cache"
os.environ["RAPIDOCR_MODEL_DIR"] = "/tmp/rapidocr_cache"

from docling.document_converter import DocumentConverter, PdfFormatOption, WordFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat
import tempfile
import re
import gc

st.set_page_config(
    page_title="Universal Markdown Converter",
    page_icon="📄",
    layout="wide"
)

st.title("📄 Universal Markdown Schema Matcher")
st.write("Convert PDFs and Word docs into mathematically identical layouts with strict table mapping.")

@st.cache_resource
def get_cloud_converter():
    pdf_options = PdfPipelineOptions()
    pdf_options.do_ocr = False  # Speeds up conversion and prevents folder permission blocks
    pdf_options.do_table_structure = True  # Locks tables into exact chronological sections (e.g., 2.2)
    
    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options),
            InputFormat.DOCX: WordFormatOption()
        }
    )

converter = get_cloud_converter()

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
        # Side-by-side loading slots
        status_cols = st.columns(len(uploaded_files))
        
        for idx, uploaded_file in enumerate(uploaded_files):
            with status_cols[idx]:
                with st.spinner(f"AI parsing structure of {uploaded_file.name}..."):
                    try:
                        suffix = f".{uploaded_file.name.split('.')[-1]}".lower()
                        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                            temp_file.write(uploaded_file.getvalue())
                            temp_file_path = temp_file.name

                        # Run unified AI structural extraction
                        result = converter.convert(temp_file_path)
                        raw_md = result.document.export_to_markdown()
                        
                        # Apply identical spacing and schema filtering
                        converted_markdowns[idx] = normalize_markdown_format(raw_md)
                        
                        os.remove(temp_file_path)
                        gc.collect()
                        
                        st.success(f"📄 Doc {idx+1} Fully Standardized")
                        
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
                        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                            os.remove(temp_file_path)

        # --- TRUE INDEPENDENT SIDE-BY-SIDE INTERFACE DISPLAY ---
        if len(uploaded_files) == 2 and 0 in converted_markdowns and 1 in converted_markdowns:
            st.markdown("---")
            st.header("🔍 Identical Layout Side-by-Side View")
            
            diff_cols = st.columns(2)
            
            with diff_cols[0]:
                st.markdown(f"**Left Column: {uploaded_files[0].name}**")
                st.text_area(
                    label="Left Stream",
                    value=converted_markdowns[0],  # Pulls ONLY Document 1
                    height=650,
                    key="side_view_doc1",
                    label_visibility="collapsed"
                )
                
            with diff_cols[1]:
                st.markdown(f"**Right Column: {uploaded_files[1].name}**")
                st.text_area(
                    label="Right Stream",
                    value=converted_markdowns[1],  # Pulls ONLY Document 2
                    height=650,
                    key="side_view_doc2",
                    label_visibility="collapsed"
                )
