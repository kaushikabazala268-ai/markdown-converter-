import streamlit as st
import difflib
import os
import docx2txt
import pdfplumber

# Force wide page layout to handle large table arrays cleanly
st.set_page_config(page_title="Perfect Document Diff Matrix", layout="wide")

def convert_to_markdown_table(table_data):
    """Converts raw list matrices into clean, standard Markdown pipe tables."""
    if not table_data or not table_data[0]:
        return ""
        
    markdown_lines = []
    
    # Process and clean Header values
    headers = [str(cell).strip().replace("\n", " ") if cell else "" for cell in table_data[0]]
    markdown_lines.append("| " + " | ".join(headers) + " |")
    
    # Generate structural layout separator line
    separators = ["---" for _ in headers]
    markdown_lines.append("| " + " | ".join(separators) + " |")
    
    # Process body rows
    for row in table_data[1:]:
        clean_row = [str(cell).strip().replace("\n", " ") if cell else "" for cell in row]
        # Skip completely empty filler rows
        if any(clean_row):
            markdown_lines.append("| " + " | ".join(clean_row) + " |")
            
    return "\n".join(markdown_lines)

def extract_document_as_markdown(uploaded_file):
    """Extracts tables into real Markdown strings and fallback lines without losing structure."""
    if uploaded_file is None:
        return ""
    
    file_ext = uploaded_file.name.split(".")[-1].lower()
    
    try:
        if file_ext in ["txt", "md"]:
            return uploaded_file.read().decode("utf-8")
            
        elif file_ext == "docx":
            return docx2txt.process(uploaded_file)
            
        elif file_ext == "pdf":
            output_blocks = []
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
                    # Target structured text grids first
                    tables = page.extract_tables(table_settings={
                        "vertical_strategy": "text", 
                        "horizontal_strategy": "text"
                    })
                    if tables:
                        for table in tables:
                            md_table = convert_to_markdown_table(table)
                            if md_table:
                                output_blocks.append(md_table)
                    else:
                        # Fallback to absolute textual line layouts if no grid lines exist
                        page_text = page.extract_text(layout=True)
                        if page_text:
                            output_blocks.append(page_text)
            return "\n\n".join(output_blocks)
            
    except Exception as e:
        st.error(f"Error compiling layout structure for {uploaded_file.name}: {str(e)}")
        return ""
    return ""

def main():
    # Global UI Theme Override: Monospace layout grids, zero text strikethroughs, clean padding blocks
    st.markdown("""
    <style>
        @import url('https://googleapis.com');

        html, body, [data-testid="stAppViewContainer"], .stMarkdown, p, h1, h2, h3, span {
            font-family: 'Inter', sans-serif !important;
        }

        /* Markdown Live Workspace Container Styles */
        .markdown-workspace-view {
            background-color: #0d1117;
            color: #c9d1d9;
            padding: 24px;
            border-radius: 8px;
            border: 1px solid #30363d;
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 13px !important;
            line-height: 1.6 !important;
            overflow-x: auto;
        }

        /* Native markdown table elements spacing rules */
        .markdown-workspace-view table {
            width: 100% !important;
            margin: 15px 0 !important;
            border-collapse: collapse !important;
            border: 1px solid #30363d !important;
        }
        .markdown-workspace-view th {
            background-color: #161b22 !important;
            padding: 10px 14px !important;
            border: 1px solid #30363d !important;
            font-weight: 600 !important;
            color: #ffffff !important;
        }
        .markdown-workspace-view td {
            padding: 10px 14px !important;
            border: 1px solid #21262d !important;
        }

        /* Clean highlight states without any line-through or strikethrough decorations */
        .pure-highlight-add {
            color: #3fb950 !important;
            font-weight: 600;
            background-color: rgba(46, 160, 67, 0.15) !important;
            padding: 4px 6px;
            margin: 2px 0;
            border-radius: 4px;
            text-decoration: none !important;
        }
        .pure-highlight-del {
            color: #f85149 !important;
            font-weight: 600;
            background-color: rgba(248, 51, 60, 0.15) !important;
            padding: 4px 6px;
            margin: 2px 0;
            border-radius: 4px;
            text-decoration: none !important;
        }
        .pure-highlight-mod {
            color: #dbb32d !important;
            font-weight: 600;
            background-color: rgba(218, 165, 32, 0.15) !important;
            padding: 4px 6px;
            margin: 2px 0;
            border-radius: 4px;
            text-decoration: none !important;
        }
    </style>
    """, unsafe_allow_html=True)

    st.title("📄 True Markdown Table Diff Matrix")
    st.caption("Parses complex PDF/Word grids into authentic Markdown elements.")
    
    st.sidebar.header("Document Sources")
    uploaded_old = st.sidebar.file_uploader("Upload Original File", type=["txt", "md", "docx", "pdf"])
    uploaded_new = st.sidebar.file_uploader("Upload Modified File", type=["txt", "md", "docx", "pdf"])
    
    if not uploaded_old or not uploaded_new:
        st.info("Please upload both items in the sidebar configuration panel to render the comparison view.")
        return

    # Extract tables into real Markdown structural arrays
    md_text1 = extract_document_as_markdown(uploaded_old)
    md_text2 = extract_document_as_markdown(uploaded_new)
    
    lines1 = md_text1.splitlines()
    lines2 = md_text2.splitlines()
    
    matcher = difflib.SequenceMatcher(None, lines1, lines2)
    
    all_output = []
    added_output = []
    deleted_output = []
    modified_output = []
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            for line in lines1[i1:i2]:
                all_output.append(line)
        
        elif tag == 'replace':
            for line in lines1[i1:i2]:
                styled = f'<div class="pure-highlight-mod">{line}</div>'
                all_output.append(styled)
                modified_output.append(styled)
            for line in lines2[j1:j2]:
                styled = f'<div class="pure-highlight-mod">{line}</div>'
                all_output.append(styled)
                modified_output.append(styled)
                
        elif tag == 'delete':
            for line in lines1[i1:i2]:
                styled = f'<div class="pure-highlight-del">{line}</div>'
                all_output.append(styled)
                deleted_output.append(styled)
                
        elif tag == 'insert':
            for line in lines2[j1:j2]:
                styled = f'<div class="pure-highlight-add">{line}</div>'
                all_output.append(styled)
                added_output.append(styled)

    # Filtering Panel Column Grid Navigation
    col1, col2, col3, col4 = st.columns(4)
    if "display_state" not in st.session_state:
        st.session_state.display_state = "Show All"
        
    if col1.button("Show All", use_container_width=True): st.session_state.display_state = "Show All"
    if col2.button(f"Added ({len(added_output)})", use_container_width=True): st.session_state.display_state = "Added"
    if col3.button(f"Deleted ({len(deleted_output)})", use_container_width=True): st.session_state.view_state = "Deleted"
    if col4.button(f"Modified ({len(modified_output)})", use_container_width=True): st.session_state.display_state = "Modified"

    # Select targeted lines string mapping
    if st.session_state.display_state == "Show All":
        final_markdown_string = "\n".join(all_output)
    elif st.session_state.display_state == "Added":
        final_markdown_string = "\n".join(added_output) if added_output else "No data blocks added."
    elif st.session_state.display_state == "Deleted":
        final_markdown_string = "\n".join(deleted_output) if deleted_output else "No data blocks deleted."
    elif st.session_state.display_state == "Modified":
        final_markdown_string = "\n".join(modified_output) if modified_output else "No modifications identified on data grids."

    st.subheader(f"Current Structure: {st.session_state.display_state}")
    
    # Process rendering of actual Markdown tables and elements
    st.markdown(f'<div class="markdown-workspace-view">{final_markdown_string}</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
