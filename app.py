import streamlit as st
import difflib
import os
import docx2txt
import pdfplumber

# Set page layout to wide mode for maximum table view space
st.set_page_config(page_title="Perfect Document Diff Matrix", layout="wide")

def highlight_cell_text(text1, text2):
    """Compares two cell text strings word-by-word. 
    Applies red/green color boxes to changes with NO strikethroughs.
    """
    if not text1 and not text2:
        return ""
    
    words1 = str(text1).split() if text1 else []
    words2 = str(text2).split() if text2 else []
    
    sm = difflib.SequenceMatcher(None, words1, words2)
    output_html = []
    
    is_modified = False
    
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            output_html.append(" ".join(words1[i1:i2]))
        elif tag == 'replace':
            is_modified = True
            if words1[i1:i2]:
                output_html.append(f'<span class="diff-del">{" ".join(words1[i1:i2])}</span>')
            if words2[j1:j2]:
                output_html.append(f'<span class="diff-add">{" ".join(words2[j1:j2])}</span>')
        elif tag == 'delete':
            is_modified = True
            output_html.append(f'<span class="diff-del">{" ".join(words1[i1:i2])}</span>')
        elif tag == 'insert':
            is_modified = True
            output_html.append(f'<span class="diff-add">{" ".join(words2[j1:j2])}</span>')
            
    return " ".join(output_html), is_modified

def process_and_diff_pdfs(file1, file2):
    """Extracts tables from both files, matches them, and highlights cellular differences."""
    with pdfplumber.open(file1) as pdf1, pdfplumber.open(file2) as pdf2:
        # Extract tables from all pages
        tables1 = []
        for p in pdf1.pages:
            t = p.extract_tables()
            if t: tables1.extend(t)
            
        tables2 = []
        for p in pdf2.pages:
            t = p.extract_tables()
            if t: tables2.extend(t)
            
    # Fallback if no tables are detected programmatically
    if not tables1 or not tables2:
        return "<p style='color:#c9d1d9;'>No structural tables detected in one or both files.</p>", 0, 0, 0

    all_tables_html = []
    added_count = 0
    deleted_count = 0
    modified_count = 0

    # Compare tables one by one
    max_tables = max(len(tables1), len(tables2))
    for t_idx in range(max_tables):
        t1 = tables1[t_idx] if t_idx < len(tables1) else []
        t2 = tables2[t_idx] if t_idx < len(tables2) else []
        
        if not t1: # Table was completely added in file 2
            added_count += 1
            table_html = '<table class="diff-table table-added">'
            for row in t2:
                table_html += "<tr>" + "".join([f'<td><span class="diff-add">{cell if cell else ""}</span></td>' for cell in row]) + "</tr>"
            table_html += "</table><br>"
            all_tables_html.append((table_html, 'added'))
            continue
            
        if not t2: # Table was completely deleted from file 1
            deleted_count += 1
            table_html = '<table class="diff-table table-deleted">'
            for row in t1:
                table_html += "<tr>" + "".join([f'<td><span class="diff-del">{cell if cell else ""}</span></td>' for cell in row]) + "</tr>"
            table_html += "</table><br>"
            all_tables_html.append((table_html, 'deleted'))
            continue

        # Compare row data inside the matched tables
        table_html = '<table class="diff-table">'
        table_has_modifications = False
        
        max_rows = max(len(t1), len(t2))
        for r_idx in range(max_rows):
            row1 = t1[r_idx] if r_idx < len(t1) else []
            row2 = t2[r_idx] if r_idx < len(t2) else []
            
            table_html += "<tr>"
            max_cells = max(len(row1), len(row2))
            
            for c_idx in range(max_cells):
                c1 = row1[c_idx] if c_idx < len(row1) else ""
                c2 = row2[c_idx] if c_idx < len(row2) else ""
                
                # Check for word mutations inside this specific grid cell
                highlighted_text, cell_was_mod = highlight_cell_text(c1, c2)
                if cell_was_mod:
                    table_has_modifications = True
                    
                table_html += f"<td>{highlighted_text}</td>"
            table_html += "</tr>"
            
        table_html += "</table><br>"
        
        if table_has_modifications:
            modified_count += 1
            all_tables_html.append((table_html, 'modified'))
        else:
            all_tables_html.append((table_html, 'equal'))

    return all_tables_html, added_count, deleted_count, modified_count

def main():
    # Global UI Theme Stylesheet: Monospace tables, soft backgrounds, NO text strikethroughs
    st.markdown("""
    <style>
        @import url('https://googleapis.com');

        html, body, [data-testid="stAppViewContainer"], .stMarkdown, p, h1, h2, h3, span {
            font-family: 'Inter', sans-serif !important;
        }

        /* Master View Panel Container */
        .workspace-view {
            background-color: #0d1117;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #30363d;
            overflow-x: auto;
        }

        /* Perfect Monospace Table Layout Configurations */
        .diff-table {
            width: 100%;
            border-collapse: collapse;
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 13px !important;
            line-height: 1.5 !important;
            color: #c9d1d9;
            background-color: #161b22;
            border: 1px solid #30363d;
            margin-bottom: 20px;
        }
        
        .diff-table td {
            padding: 10px 14px;
            border: 1px solid #30363d;
            vertical-align: top;
        }
        
        /* Table-level bulk state backgrounds */
        .table-added { background-color: rgba(46, 160, 67, 0.05); }
        .table-deleted { background-color: rgba(248, 51, 60, 0.05); }

        /* Laser-Focused Word Tints: Pure backgrounds, ABSOLUTELY NO line crossing */
        .diff-add {
            background-color: rgba(46, 160, 67, 0.25) !important;
            color: #3fb950 !important;
            padding: 2px 6px !important;
            border-radius: 4px !important;
            font-weight: 500 !important;
            text-decoration: none !important;
            display: inline-block;
        }
        .diff-del {
            background-color: rgba(248, 51, 60, 0.25) !important;
            color: #f85149 !important;
            padding: 2px 6px !important;
            border-radius: 4px !important;
            font-weight: 500 !important;
            text-decoration: none !important;
            display: inline-block;
        }
    </style>
    """, unsafe_allow_html=True)

    st.title("📄 Perfect Table Grid Diff Matrix")
    st.caption("Preserves full table structure with word-level red/green background highlight tracking.")
    
    st.sidebar.header("Document Sources")
    uploaded_old = st.sidebar.file_uploader("Upload Original File", type=["pdf"])
    uploaded_new = st.sidebar.file_uploader("Upload Modified File", type=["pdf"])
    
    if not uploaded_old or not uploaded_new:
        st.info("Please upload both PDF files in the sidebar panel to view your tables.")
        return

    # Compile the tables and run word-level cell analysis
    tables_html_list, added_num, deleted_num, modified_num = process_and_diff_pdfs(uploaded_old, uploaded_new)

    # Filter Action Command Buttons Setup Layout
    col1, col2, col3, col4 = st.columns(4)
    if "filter_state" not in st.session_state:
        st.session_state.filter_state = "Show All"
        
    if col1.button("Show All", use_container_width=True): st.session_state.filter_state = "Show All"
    if col2.button(f"Added ({added_num})", use_container_width=True): st.session_state.filter_state = "Added"
    if col3.button(f"Deleted ({deleted_num})", use_container_width=True): st.session_state.filter_state = "Deleted"
    if col4.button(f"Modified ({modified_num})", use_container_width=True): st.session_state.filter_state = "Modified"

    # Assemble filtered tables based on selected view state
    rendered_tables = []
    for html_code, status in tables_html_list:
        if st.session_state.filter_state == "Show All":
            rendered_tables.append(html_code)
        elif st.session_state.filter_state == "Added" and status == 'added':
            rendered_tables.append(html_code)
        elif st.session_state.filter_state == "Deleted" and status == 'deleted':
            rendered_tables.append(html_code)
        elif st.session_state.filter_state == "Modified" and status == 'modified':
            rendered_tables.append(html_code)

    final_view_html = "".join(rendered_tables) if rendered_tables else "<p style='color:#c9d1d9;'>No tables match this filter criteria.</p>"

    st.subheader(f"Viewing State: {st.session_state.filter_state}")
    
    # Render the full tables with inline word highlights perfectly preserved
    st.markdown(f'<div class="workspace-view">{final_view_html}</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
