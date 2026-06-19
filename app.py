import streamlit as st
import difflib
import os
import docx2txt
import pdfplumber

# Set page layout config to wide mode for absolute maximum text space
st.set_page_config(page_title="Perfect Document Diff Matrix", layout="wide")

def extract_text(uploaded_file):
    """Extracts clean text strings from TXT, MD, DOCX, or PDF while keeping spacing."""
    if uploaded_file is None:
        return ""
    
    file_ext = uploaded_file.name.split(".")[-1].lower()
    
    try:
        if file_ext in ["txt", "md"]:
            return uploaded_file.read().decode("utf-8")
            
        elif file_ext == "docx":
            return docx2txt.process(uploaded_file)
            
        elif file_ext == "pdf":
            # Using pdfplumber to strictly preserve layout matrices and table spaces
            text_slices = []
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
                    # extract_text(layout=True) forces spaces to preserve table grids
                    page_text = page.extract_text(layout=True)
                    if page_text:
                        text_slices.append(page_text)
            return "\n".join(text_slices)
            
    except Exception as e:
        st.error(f"Error parsing {uploaded_file.name}: {str(e)}")
        return ""
    return ""

def main():
    # Custom embedded styling inside Streamlit to load external typography and freeze layouts
    st.markdown("""
    <style>
        /* Import premium fonts from Google Fonts API */
        @import url('https://googleapis.com');

        /* Force Inter Font styling on global application text wrapper layers */
        html, body, [data-testid="stAppViewContainer"], .stMarkdown, .stButton button, p, h1, h2, h3, span {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        }
        
        /* Master Headings typography tuning */
        h1 {
            font-weight: 700 !important;
            letter-spacing: -0.02em !important;
        }
        
        /* Custom UI Buttons styling overrides */
        .stButton button {
            font-weight: 600 !important;
            font-size: 13px !important;
            letter-spacing: -0.01em !important;
            border-radius: 8px !important;
            transition: all 0.2s ease;
        }

        /* Laser-focused locked typography constraints for the Document Matrix data rows */
        .diff-container, .line-row, code, pre {
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 13px !important;
            line-height: 1.45 !important;
            letter-spacing: 0em !important;
        }
        
        /* Layout block definitions */
        .diff-container {
            background-color: #0d1117;
            color: #c9d1d9;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #30363d;
            white-space: pre;
            overflow-x: auto;
            margin-top: 10px;
        }
        .line-row {
            margin: 0 !important;
            padding: 1px 0 !important;
            min-height: 1.45em;
        }
        .highlight-add {
            background-color: rgba(46, 160, 67, 0.22);
            color: #3fb950;
            display: inline-block;
            width: 100%;
            font-weight: 500;
        }
        .highlight-del {
            background-color: rgba(248, 51, 60, 0.22);
            color: #f85149;
            text-decoration: line-through;
            display: inline-block;
            width: 100%;
            font-weight: 500;
        }
    </style>
    """, unsafe_allow_html=True)

    st.title("📄 Perfect Document Diff Matrix")
    st.caption("Supports: PDF (via pdfplumber Layout engine), DOCX, TXT, and MD formats")
    
    st.sidebar.header("Document Sources")
    uploaded_old = st.sidebar.file_uploader("Upload Original File", type=["txt", "md", "docx", "pdf"])
    uploaded_new = st.sidebar.file_uploader("Upload Modified File", type=["txt", "md", "docx", "pdf"])
    
    if not uploaded_old or not uploaded_new:
        st.info("Please upload both the original and modified document in the sidebar to view changes.")
        return

    text1 = extract_text(uploaded_old)
    text2 = extract_text(uploaded_new)
    
    lines1 = text1.splitlines()
    lines2 = text2.splitlines()
    
    matcher = difflib.SequenceMatcher(None, lines1, lines2)
    
    all_rows = []
    added_rows = []
    deleted_rows = []
    modified_rows = []
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            for line in lines1[i1:i2]:
                safe_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                row_html = f'<div class="line-row">{safe_line}</div>'
                all_rows.append(row_html)
        
        elif tag == 'replace':
            for line in lines1[i1:i2]:
                safe_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                row_html = f'<div class="line-row"><span class="highlight-del">{safe_line}</span></div>'
                all_rows.append(row_html)
                modified_rows.append(row_html)
            for line in lines2[j1:j2]:
                safe_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                row_html = f'<div class="line-row"><span class="highlight-add">{safe_line}</span></div>'
                all_rows.append(row_html)
                modified_rows.append(row_html)
                
        elif tag == 'delete':
            for line in lines1[i1:i2]:
                safe_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                row_html = f'<div class="line-row"><span class="highlight-del">{safe_line}</span></div>'
                all_rows.append(row_html)
                deleted_rows.append(row_html)
                
        elif tag == 'insert':
            for line in lines2[j1:j2]:
                safe_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                row_html = f'<div class="line-row"><span class="highlight-add">{safe_line}</span></div>'
                all_rows.append(row_html)
                added_rows.append(row_html)

    # Interactive Navigation Action Buttons using Native Streamlit Columns
    col1, col2, col3, col4 = st.columns(4)
    
    if "current_view" not in st.session_state:
        st.session_state.current_view = "Show All"
        
    if col1.button("Show All", use_container_width=True):
        st.session_state.current_view = "Show All"
    if col2.button(f"Added ({len(added_rows)})", use_container_width=True):
        st.session_state.current_view = "Added"
    if col3.button(f"Deleted ({len(deleted_rows)})", use_container_width=True):
        st.session_state.current_view = "Deleted"
    if col4.button(f"Modified ({len(modified_rows)})", use_container_width=True):
        st.session_state.current_view = "Modified"

    if st.session_state.current_view == "Show All":
        selected_data = "".join(all_rows)
    elif st.session_state.current_view == "Added":
        selected_data = "".join(added_rows) if added_rows else '<div class="line-row">No records found.</div>'
    elif st.session_state.current_view == "Deleted":
        selected_data = "".join(deleted_rows) if deleted_rows else '<div class="line-row">No records found.</div>'
    elif st.session_state.current_view == "Modified":
        selected_data = "".join(modified_rows) if modified_rows else '<div class="line-row">No records found.</div>'

    st.subheader(f"Viewing: {st.session_state.current_view}")
    st.markdown(f'<div class="diff-container">{selected_data}</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
