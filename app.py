import streamlit as st
from docling.document_converter import DocumentConverter, PdfFormatOption, WordFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat
import tempfile
import difflib
import os
import gc

st.set_page_config(
    page_title="Universal Markdown Schema Matcher",
    page_icon="📄",
    layout="wide"
)

st.title("📄 Universal Markdown Schema Matcher & Diff Viewer")
st.write("Upload any two files (Word or PDF) to convert them into identical structural formats and see live text changes.")

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
        # Side-by-side processing columns
        cols = st.columns(len(uploaded_files))
        
        for idx, uploaded_file in enumerate(uploaded_files):
            with cols[idx]:
                st.subheader(f"📄 Document {idx+1}: {uploaded_file.name}")
                
                with st.spinner("Parsing structure and tables..."):
                    try:
                        suffix = f".{uploaded_file.name.split('.')[-1]}".lower()
                        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                            temp_file.write(uploaded_file.getvalue())
                            temp_file_path = temp_file.name

                        result = converter.convert(temp_file_path)
                        markdown_output = result.document.export_to_markdown()
                        
                        # Save converted output to cross-compare later
                        converted_markdowns[idx] = markdown_output
                        
                        os.remove(temp_file_path)
                        gc.collect()
                        
                        st.success(f"Document {idx+1} complete!")
                        
                        base_name, _ = os.path.splitext(uploaded_file.name)
                        st.download_button(
                            label=f"📥 Download Markdown {idx+1}",
                            data=markdown_output,
                            file_name=f"{base_name}.md",
                            mime="text/markdown",
                            key=f"dl_btn_{idx}"
                        )
                        
                        with st.expander("👀 View Formatting", expanded=True):
                            st.text_area(
                                label="Raw Content", 
                                value=markdown_output, 
                                height=400,
                                key=f"text_area_{idx}"
                            )
                            
                    except Exception as e:
                        st.error(f"Processing error: {e}")
                        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                            os.remove(temp_file_path)
                        gc.collect()

        # --- LIVE NATIVE SIDE-BY-SIDE DIFF VIEW SECTION ---
        if len(uploaded_files) == 2 and 0 in converted_markdowns and 1 in converted_markdowns:
            st.markdown("---")
            st.header("🔍 Interactive Document Difference Analysis")
            st.write("Below is a side-by-side comparison. Use the scrollbars to look through both converted documents simultaneously.")
            
            # Split strings into line arrays for comparison calculations
            lines1 = converted_markdowns[0].splitlines()
            lines2 = converted_markdowns[1].splitlines()
            
            # Use Python's built-in engine to generate a clean, responsive HTML table view
            diff_engine = difflib.HtmlDiff()
            diff_html = diff_engine.make_file(
                lines1, 
                lines2, 
                fromdesc=uploaded_files[0].name, 
                todesc=uploaded_files[1].name
            )
            
            # Safely render the HTML structure directly inside Streamlit
            st.components.v1.html(diff_html, height=600, scrolling=True)
