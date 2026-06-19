import streamlit as st
import difflib
import os
import docx2txt
import pdfplumber

# Force wide layout to accommodate the side-by-side markdown comparison engine matrix
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
            text_slices = []
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text(layout=True)
                    if page_text:
                        text_slices.append(page_text)
            return "\n".join(text_slices)
            
    except Exception as e:
        st.error(f"Error parsing {uploaded_file.name}: {str(e)}")
        return ""
    return ""

def highlight_words(line1, line2):
    """Compares two lines word-by-word and applies styling strictly to changed words."""
    words1 = line1.split()
    words2 = line2.split()
    
    sm = difflib.SequenceMatcher(None, words1, words2)
    
    out1, out2 = [], []
    
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            out1.extend(words1[i1:i2])
            out2.extend(words2[j1:j2])
        elif tag == 'replace':
            # Highlight only the specific word changed instead of striking through everything
            out1.append(f'<span class="word-del">{" ".join(words1[i1:i2])}</span>')
            out2.append(f'<span class="word-add">{" ".join(words2[j1:j2])}</span>')
        elif tag == 'delete':
            out1.append(f'<span class="word-del">{" ".join(words1[i1:i2])}</span>')
        elif tag == 'insert':
            out2.append(f'<span class="word-add">{" ".join(words2[j1:j2])}</span>')
            
    return " ".join(out1), " ".join(out2)

def main():
    # Premium CSS layout lock: forces monospace matrix grids, hides default markdown table padding
    st.markdown("""
    <style>
        @import url('https://googleapis.com');

        html, body, [data-testid="stAppViewContainer"], .stMarkdown, p, h1, h2, h3, span {
            font-family: 'Inter', sans-serif !important;
        }
        
        /* Clear margins to remove awkward spacing gaps */
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
        }

        /* Pure Monospace Table Matrix Formatting rules */
        .diff-table {
            width: 100%;
            border-collapse: collapse;
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 13px !important;
            line-height: 1.5 !important;
            background-color: #0d1117;
            color: #c9d1d9;
            border: 1px solid #30363d;
        }
        
        .diff-table th {
            background-color: #161b22;
            padding: 10px;
            text-align: left;
            border-bottom: 2px solid #30363d;
            font-family: 'Inter', sans-serif !important;
            font-weight: 600;
        }
        
        .diff-table td {
            padding: 2px 8px;
            border-bottom: 1px solid #21262d;
            white-space: pre-wrap;
            vertical-align: top;
            width: 50%;
        }

        /* Row background tints based on layout states */
        .row-equal { background-color: transparent; }
        .row-added { background-color: rgba(46, 160, 67, 0.1); }
        .row-deleted { background-color: rgba(248, 51, 60, 0.1); }
        .row-modified { background-color: rgba(210, 153, 34, 0.1); }

        /* Laser-accurate inline changes highlights (No global strikethroughs) */
        .word-add {
            background-color: rgba(46, 160, 67, 0.3);
            color: #3fb950;
            padding: 0 2px;
            border-radius: 3px;
        }
        .word-del {
            background-color: rgba(248, 51, 60, 0.3);
            color: #f85149;
            text-decoration: line-through;
            padding: 0 2px;
            border-radius: 3px;
        }
    </style>
    """, unsafe_allow_html=True)

    st.title("📄 Perfect Document Diff Matrix")
    st.caption("Side-by-Side structural Markdown mapping with word-level highlight resolution.")
    
    st.sidebar.header("Document Sources")
    uploaded_old = st.sidebar.file_uploader("Upload Original File", type=["txt", "md", "docx", "pdf"])
    uploaded_new = st.sidebar.file_uploader("Upload Modified File", type=["txt", "md", "docx", "pdf"])
    
    if not uploaded_old or not uploaded_new:
        st.info("Please upload both documents in the sidebar configuration drawer to run comparison calculations.")
        return

    text1 = extract_text(uploaded_old)
    text2 = extract_text(uploaded_new)
    
    lines1 = text1.splitlines()
    lines2 = text2.splitlines()
    
    matcher = difflib.SequenceMatcher(None, lines1, lines2)
    
    # Global arrays holding compiled data mappings
    all_matrix = []
    added_matrix = []
    deleted_matrix = []
    modified_matrix = []
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            for line in lines1[i1:i2]:
                row = f'<tr class="row-equal"><td>{line}</td><td>{line}</td></tr>'
                all_matrix.append(row)
                
        elif tag == 'replace':
            # Balance blocks line-by-line to preserve layout alignment tracking
            max_len = max(i2 - i1, j2 - j1)
            for idx in range(max_len):
                l1 = lines1[i1 + idx] if (i1 + idx) < i2 else ""
                l2 = lines2[j1 + idx] if (j1 + idx) < j2 else ""
                
                hl1, hl2 = highlight_words(l1, l2)
                row = f'<tr class="row-modified"><td>{hl1}</td><td>{hl2}</td></tr>'
                all_matrix.append(row)
                modified_matrix.append(row)
                
        elif tag == 'delete':
            for line in lines1[i1:i2]:
                row = f'<tr class="row-deleted"><td><span class="word-del">{line}</span></td><td></td></tr>'
                all_matrix.append(row)
                deleted_matrix.append(row)
                
        elif tag == 'insert':
            for line in lines2[j1:j2]:
                row = f'<tr class="row-added"><td></td><td><span class="word-add">{line}</span></td></tr>'
                all_matrix.append(row)
                added_matrix.append(row)

    # Filtering Panel Buttons Navigation layout matrix
    col1, col2, col3, col4 = st.columns(4)
    if "view_state" not in st.session_state:
        st.session_state.view_state = "Show All"
        
    if col1.button("Show All", use_container_width=True): st.session_state.view_state = "Show All"
    if col2.button(f"Added ({len(added_matrix)})", use_container_width=True): st.session_state.view_state = "Added"
    if col3.button(f"Deleted ({len(deleted_matrix)})", use_container_width=True): st.session_state.view_state = "Deleted"
    if col4.button(f"Modified ({len(modified_matrix)})", use_container_width=True): st.session_state.view_state = "Modified"

    # Select proper matrix array data string block
    if st.session_state.view_state == "Show All":
        active_rows = "".join(all_matrix)
    elif st.session_state.view_state == "Added":
        active_rows = "".join(added_matrix) if added_matrix else '<tr><td colspan="2">No elements found.</td></tr>'
    elif st.session_state.view_state == "Deleted":
        active_rows = "".join(deleted_matrix) if deleted_matrix else '<tr><td colspan="2">No elements found.</td></tr>'
    elif st.session_state.view_state == "Modified":
        active_rows = "".join(modified_matrix) if modified_matrix else '<tr><td colspan="2">No elements found.</td></tr>'

    st.subheader(f"Current Matrix Target: {st.session_state.view_state}")
    
    # Generate the perfect side-by-side document layout markdown table 
    table_markdown = f"""
    <table class="diff-table">
        <thead>
            <tr>
                <th>Original Layout State ({uploaded_old.name})</th>
                <th>Modified Layout State ({uploaded_new.name})</th>
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
