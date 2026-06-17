import streamlit as st
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat
import tempfile
import os
import gc  # Garbage collection to free up RAM

# Set up page configuration
st.set_page_config(
    page_title="Universal Markdown Converter",
    page_icon="📄",
    layout="centered"
)

st.title("📄 Universal Markdown Converter")
st.write("Convert PDFs, Word docs, PowerPoint slides, and HTML into clean Markdown.")

# Initialize Docling Converter with Memory-Optimized Options
@st.cache_resource
def get_optimized_converter():
    # 1. Set up optimized PDF pipeline options to prevent memory crashes
    pipeline_options = PdfPipelineOptions()
    
    # Process pages in very small chunks to prevent std::bad_alloc
    pipeline_options.page_batch_size = 1 
    
    # Disable heavy layout/enrichment models that drain RAM
    pipeline_options.do_formula_classification = False
    pipeline_options.generate_page_images = False
    pipeline_options.generate_picture_images = False
    
    # 2. Bind these memory-saving options specifically to the PDF format
    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

converter = get_optimized_converter()

# File uploader supporting multiple common formats
uploaded_file = st.file_uploader(
    "Choose a file to convert", 
    type=["pdf", "docx", "pptx", "html", "htm"]
)

if uploaded_file is not None:
    st.info(f"Processing: **{uploaded_file.name}**")
    
    with st.spinner("Converting file to Markdown..."):
        try:
            # Docling requires a file path, so we write the uploaded bytes to a temporary file
            suffix = f".{uploaded_file.name.split('.')[-1]}"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                temp_file.write(uploaded_file.getvalue())
                temp_file_path = temp_file.name

            # Run the optimized Docling conversion
            result = converter.convert(temp_file_path)
            markdown_output = result.document.export_to_markdown()
            
            # Clean up the temporary file immediately
            os.remove(temp_file_path)
            
            # Force clean memory leaks from previous page caches
            gc.collect() 
            
            st.success("Conversion successful!")
            
            # Create download button for the resulting .md file
            base_name, _ = os.path.splitext(uploaded_file.name)
            output_filename = f"{base_name}.md"
            
            st.download_button(
                label="📥 Download Markdown File",
                data=markdown_output,
                file_name=output_filename,
                mime="text/markdown"
            )
            
            # Preview section
            with st.expander("👀 Preview Generated Markdown", expanded=True):
                st.text_area(
                    label="Markdown Raw Text", 
                    value=markdown_output, 
                    height=400
                )
                
        except Exception as e:
            st.error(f"An error occurred during conversion: {e}")
            # Ensure cleanup even if it crashes
            if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            gc.collect()