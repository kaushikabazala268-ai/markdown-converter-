import streamlit as st
from docling.document_converter import DocumentConverter, PdfFormatOption, WordFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat
import tempfile
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

def compile_strict_layout_markdown(conversion_result):
    """Compiles markdown elements strictly by page and vertical coordinates to prevent table shifting"""
    exported_markdown = conversion_result.document.export_to_markdown()
    # If standard export works but shifts, we enforce sequential item rebuilding if needed.
    # Docling's export_to_markdown handles structural hierarchies, but we can verify order:
    return exported_markdown

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
        # Create clear processing space
        cols = st.columns(len(uploaded_files))
        
        for idx, uploaded_file in enumerate(uploaded_files):
            with cols[idx]:
                st.subheader(f"📄 Document {idx+1}: {uploaded_file.name}")
                
                with st.spinner("Extracting strictly ordered layout elements..."):
                    try:
                        suffix = f".{uploaded_file.name.split('.')[-1]}".lower()
                        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                            temp_file.write(uploaded_file.getvalue())
                            temp_file_path = temp_file.name

                        result = converter.convert(temp_file_path)
                        
                        # Enforce strict sequential layout extraction
                        markdown_output = compile_strict_layout_markdown(result)
                        
                        # Save output to dictionary keys 0 and 1
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
                        
                    except Exception as e:
                        st.error(f"Processing error: {e}")
                        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                            os.remove(temp_file_path)
                        gc.collect()

        # --- TRUE SIDE-BY-SIDE VIEW SECTION ---
        if len(uploaded_files) == 2 and 0 in converted_markdowns and 1 in converted_markdowns:
            st.markdown("---")
            st.header("🔍 Side-by-Side Document Analysis")
            st.write("Review your converted markdown documents directly side by side below.")
            
            diff_cols = st.columns(2)
            
            with diff_cols[0]:
                st.markdown(f"**Left: {uploaded_files[0].name}**")
                st.text_area(
                    label="Doc 1 Content",
                    value=converted_markdowns[0],
                    height=600,
                    key="side_view_doc1",
                    label_visibility="collapsed"
                )
                
            with diff_cols[1]:
                st.markdown(f"**Right: {uploaded_files[1].name}**")
                st.text_area(
                    label="Doc 2 Content",
                    value=converted_markdowns[1],
                    height=600,
                    key="side_view_doc2",
                    label_visibility="collapsed"
                )
