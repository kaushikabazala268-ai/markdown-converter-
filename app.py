import streamlit as st
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat
import tempfile
import os
import gc

# Set up page configuration
st.set_page_config(
    page_title="Universal Markdown Converter",
    page_icon="📄",
    layout="centered"
)

st.title("📄 Universal Markdown Converter")
st.write("Convert PDFs, Word docs, PowerPoint slides, and HTML into clean Markdown using Docling on Streamlit Cloud.")

# Initialize Docling Converter 
@st.cache_resource
def get_converter():
    # Set up pipeline configurations
    pipeline_options = PdfPipelineOptions()
    
    # Enable high-fidelity table structure mapping
    pipeline_options.do_table_structure = True 
    pipeline_options.do_formula_classification = False 
    
    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

converter = get_converter()

# File uploader supporting multiple common formats
uploaded_file = st.file_uploader(
    "Choose a file to convert", 
    type=["pdf", "docx", "pptx", "html", "htm"]
)

if uploaded_file is not None:
    st.info(f"Processing: **{uploaded_file.name}**")
    
    with st.spinner("Processing layout & structural tables..."):
        try:
            # Create a temporary file path for Docling ingestion
            suffix = f".{uploaded_file.name.split('.')[-1]}".lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                temp_file.write(uploaded_file.getvalue())
                temp_file_path = temp_file.name

            # Run the Docling conversion pipeline
            result = converter.convert(temp_file_path)
            markdown_output = result.document.export_to_markdown()
            
            # Clean up the temporary file immediately
            os.remove(temp_file_path)
            gc.collect() 
            
            st.success("Conversion successful!")
            
            # Create download button for the resulting .md file
            base_name, _ = os.path.splitext(uploaded_file.name)
            st.download_button(
                label="📥 Download Markdown File",
                data=markdown_output,
                file_name=f"{base_name}.md",
                mime="text/markdown"
            )
            
            # Interactive markdown text viewer box
            with st.expander("👀 Preview Generated Markdown", expanded=True):
                st.text_area(
                    label="Markdown Raw Text", 
                    value=markdown_output, 
                    height=400
                )
                
        except Exception as e:
            st.error(f"An error occurred during conversion: {e}")
            if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            gc.collect()
