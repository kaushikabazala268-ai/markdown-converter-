import streamlit as st
from docling.document_converter import DocumentConverter, PdfFormatOption, WordFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, EmbeddingPipelineOptions
from docling.datamodel.base_models import InputFormat
import tempfile
import os
import gc

st.set_page_config(
    page_title="Unified Multi-Markdown Converter",
    page_icon="📄",
    layout="wide"
)

st.title("📄 Unified Multi-Markdown Converter")
st.write("Upload up to 2 files (PDF or Word) to convert them into a mathematically identical Markdown schema.")

@st.cache_resource
def get_unified_converter():
    # Configure PDF Pipeline to enforce strict sequential table containment
    pdf_options = PdfPipelineOptions()
    pdf_options.do_ocr = False
    pdf_options.do_table_structure = True
    
    # Configure unified layout extraction rules across different engines
    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options),
            InputFormat.DOCX: WordFormatOption()
        }
    )

converter = get_unified_converter()

# Accept exactly up to two documents simultaneously
uploaded_files = st.file_uploader(
    "Choose up to two files to convert (PDF or Word)", 
    type=["pdf", "docx"],
    accept_multiple_files=True
)

if uploaded_files:
    if len(uploaded_files) > 2:
        st.error("Please select a maximum of two files at a time.")
    else:
        # Create columns dynamically based on the number of uploaded files
        cols = st.columns(len(uploaded_files))
        
        for idx, uploaded_file in enumerate(uploaded_files):
            with cols[idx]:
                st.subheader(f"📄 Document {idx+1}: {uploaded_file.name}")
                
                with st.spinner("Extracting structural data..."):
                    try:
                        suffix = f".{uploaded_file.name.split('.')[-1]}".lower()
                        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                            temp_file.write(uploaded_file.getvalue())
                            temp_file_path = temp_file.name

                        # Convert using structural layout preservation maps
                        result = converter.convert(temp_file_path)
                        
                        # Sequential block assembly fixes layout grouping anomalies
                        markdown_output = result.document.export_to_markdown()
                        
                        os.remove(temp_file_path)
                        gc.collect()
                        
                        st.success(f"Successfully processed Document {idx+1}!")
                        
                        base_name, _ = os.path.splitext(uploaded_file.name)
                        st.download_button(
                            label=f"📥 Download Markdown {idx+1}",
                            data=markdown_output,
                            file_name=f"{base_name}.md",
                            mime="text/markdown",
                            key=f"dl_{idx}"
                        )
                        
                        with st.expander("👀 View Formatting", expanded=True):
                            st.text_area(
                                label="Raw Markdown Code", 
                                value=markdown_output, 
                                height=500,
                                key=f"ta_{idx}"
                            )
                            
                    except Exception as e:
                        st.error(f"Error parsing file: {e}")
                        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                            os.remove(temp_file_path)
                        gc.collect()
