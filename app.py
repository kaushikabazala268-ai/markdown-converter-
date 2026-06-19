import streamlit as st
import difflib
import os
import docx2txt
import pdfplumber

# Set layout to wide to give the side-by-side markdown layout full width
st.set_page_config(page_title="Perfect Document Diff Matrix", layout="wide")

def extract_text(uploaded_file):
    """Extracts text while preserving spaces, alignments, and positioning configurations."""
    if uploaded_file is None:
        return ""
    
    file_ext = uploaded_file.name.split(".")[-1].lower()
    
    try:
        if file_ext in ["txt", "md"]:
            return uploaded_file.read().decode("utf-8")
            
        elif file_ext == "docx":
            return docx2txt.process(uploaded_file)
            
        elif file_ext == "pdf":
            text_slices = []
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
                    # layout=True keeps the absolute table positioning intact
                    page_text = page.extract_text(layout=True)
                    if page_text:
                        text_slices.append(page_text)
            return "\n".join(text_slices)
            
    except Exception as e:
        st.error(f"Error parsing {uploaded_file.name}: {str(e)}")
        return ""
    return ""

def highlight_words(line1, line2):
    """Compares individual words. Strips all line-through formatting and highlights changes."""
    words1 = line1.split()
    words2 = line2.split()
    
    sm = difflib.SequenceMatcher(None, words1, words2)
    out1, out2 = [], []
    
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            out1.extend(words1[i1:i2])
            out2.extend(words2[j1:j2])
        elif tag == 'replace':
            # Clean text coloring highlights only. Absolutely no strike-through line decorators.
            out1.append(f'<span class="only-highlight-del">{" ".join(words1[i1:i2])}</span>')
            out2.append(f'<span class="only-highlight-add">{" ".join(words2[j1:j2])}</span>')
        elif tag == 'delete':
            out1.append(f'<span class="only-highlight-del">{" ".join(words1[i1:i2])}</span>')
        elif tag == 'insert':
            out2.append(f'<span class="only-highlight-add">{" ".join(words2[j1:j2])}</span>')
            
    return " ".join(out1), " ".join(out2)

def main():
    # Premium UI Stylesheet: Completely removes background boxes, masks lines, locks monospace matrix fonts
    st.markdown("""
    <style>
        @import url('https://googleapis.com');

        html, body, [data-testid="stAppViewContainer"], .stMarkdown, p, h1, h2, h3, span {
            font-family: 'Inter', sans-serif !important;
        }

        /* Markdown Data Matrix Table Constraints */
        .diff-table {
            width: 100%;
            border-collapse: collapse;
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 13px !important;
            line-height: 1.6 !important;
            background-color: #0d1117;
            color: #c9d1d9;
            border: 1px solid #30363d;
        }
        
        .diff-table th {
            background-color: #161b22;
            padding: 12px;
            text-align: left;
            border-bottom: 2px solid #30363d;
            font-weight: 600;
        }
        
        .diff-table td {
            padding: 4px 10px;
            border-bottom: 1px solid #21262d;
            white-space: pre-wrap;
            vertical-align: top;
            width: 50%;
        }

        /* Clean Highlighting Styles: Pure color tints with zero line decorations */
        .only-highlight-add {
            color: #2ea043 !important;
            font-weight: 600;
            background: transparent !important;
            text-decoration: none !important;
        }
        .only-highlight-del {
            color: #f85149 !important;
            font-weight: 600;
            background: transparent !important;
            text-decoration: none !important;
        }
    </style>
    """, unsafe_allow_html=True)

    st.title("📄 Perfect Markdown Comparison Matrix")
    st.caption("Clean text highlighting layout with absolute structural mapping.")
    
    st.sidebar.header("Document Sources")
    uploaded_old = st.sidebar.file_uploader("Upload Original File", type=["txt", "md", "docx", "pdf"])
    uploaded_new = st.sidebar.file_uploader("Upload Modified File", type=["txt", "md", "docx", "pdf"])
    
    if not uploaded_old or not uploaded_new:
        st.info("Please upload both documents in the sidebar configuration drawer to view the comparison table.")
        return

    text1 = extract_text(uploaded_old)
    text2 = extract_text(uploaded_new)
    
    lines1 = text1.splitlines()
    lines2 = text2.splitlines()
    
    matcher = difflib.SequenceMatcher(None, lines1, lines2)
    
    all_matrix = []
    added_matrix = []
    deleted_matrix = []
    modified_matrix = []
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            for line in lines1[i1:i2]:
                row = f'<tr><td>{line}</td><td>{line}</td></tr>'
                all_matrix.append(row)
                
        elif tag == 'replace':
            max_len = max(i2 - i1, j2 - j1)
            for idx in range(max_len):
                l1 = lines1[i1 + idx] if (i1 + idx) < i2 else ""
                l2 = lines2[j1 + idx] if (j1 + idx) < j2 else ""
                
                hl1, hl2 = highlight_words(l1, l2)
                row = f'<tr><td>{hl1}</td><td>{hl2}</td></tr>'
                all_matrix.append(row)
                modified_matrix.append(row)
                
        elif tag == 'delete':
            for line in lines1[i1:i2]:
                row = f'<tr><td><span class="only-highlight-del">{line}</span></td><td></td></tr>'
                all_matrix.append(row)
                deleted_matrix.append(row)
                
        elif tag == 'insert':
            for line in lines2[j1:j2]:
                row = f'<tr><td></td><td><span class="only-highlight-add">{line}</span></td></tr>'
                all_matrix.append(row)
                added_matrix.append(row)

    # Filtering Panel Action Buttons
    col1, col2, col3, col4 = st.columns(4)
    if "view_state" not in st.session_state:
        st.session_state.view_state = "Show All"
        
    if col1.button("Show All", use_container_width=True): st.session_state.view_state = "Show All"
    if col2.button(f"Added ({len(added_matrix)})", use_container_width=True): st.session_state.view_state = "Added"
    if col3.button(f"Deleted ({len(deleted_matrix)})", use_container_width=True): st.session_state.view_state = "Deleted"
    if col4.button(f"Modified ({len(modified_matrix)})", use_container_width=True): st.session_state.view_state = "Modified"

    if st.session_state.current_view == "Show All":
        active_rows = "".join(all_matrix)
    elif st.session_state.view_state == "Added":
        active_rows = "".join(added_matrix) if added_matrix else '<tr><td colspan="2">No elements found.</td></tr>'
    elif st.session_state.view_state == "Deleted":
        active_rows = "".join(deleted_matrix) if deleted_matrix else '<tr><td colspan="2">No elements found.</td></tr>'
    elif st.session_state.view_state == "Modified":
        active_rows = "".join(modified_matrix) if modified_matrix else '<tr><td colspan="2">No elements found.</td></tr>'

    st.subheader(f"Viewing Matrix: {st.session_state.view_state}")
    
    # Generate the Markdown Side-by-Side Table Comparison Block
    table_markdown = f"""
    <table class="diff-table">
        <thead>
            <tr>
                <th>Original Code State ({uploaded_old.name})</th>
                <th>Modified Code State ({uploaded_new.name})</th>
            </tr>
        </thead>
        <tbody>
            {active_rows}
        </tbody>
    </table>
    """
    
    st.markdown(table_markdown, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
