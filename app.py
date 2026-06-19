import os

# 1. Define the complete interactive Streamlit App code (app.py)
app_script_content = """import streamlit as st
import difflib
import os

# Set page layout config to wide mode for absolute maximum text space
st.set_page_config(page_title="Perfect Document Diff Matrix", layout="wide")

def read_file(file_path):
    if not os.path.exists(file_path):
        return None
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def main():
    st.title("📄 Perfect Document Diff Matrix")
    
    # Define targets
    file1_path = "old_file.txt" 
    file2_path = "new_file.txt"
    
    # Core fallback: Allow manual uploading if files aren't in the root folder yet
    st.sidebar.header("Document Sources")
    uploaded_old = st.sidebar.file_uploader("Upload Original File", type=["txt", "md", "csv"])
    uploaded_new = st.sidebar.file_uploader("Upload Modified File", type=["txt", "md", "csv"])
    
    # Determine which file text to read
    text1 = uploaded_old.read().decode("utf-8") if uploaded_old else read_file(file1_path)
    text2 = uploaded_new.read().decode("utf-8") if uploaded_new else read_file(file2_path)
    
    if text1 is None or text2 is None:
        st.warning("Please place 'old_file.txt' and 'new_file.txt' in your repository root, or upload them via the sidebar.")
        return

    lines1 = text1.splitlines()
    lines2 = text2.splitlines()
    
    matcher = difflib.SequenceMatcher(None, lines1, lines2)
    
    # Containers to keep track of rows categorized by change type
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

    # Custom embedded styling inside Streamlit to freeze layouts, monospace alignments, and colors
    st.markdown(\"\"\"
    <style>
        .stMarkdown div pre, code, .diff-container, .line-row {
            font-family: ui-monospace, SFMono-Regular, SF Mono, Menlo, Consolas, Liberation Mono, monospace !important;
            font-size: 13px !important;
            line-height: 1.4 !important;
        }
        .diff-container {
            background-color: #0d1117;
            color: #c9d1d9;
            padding: 15px;
            border-radius: 6px;
            border: 1px solid #30363d;
            white-space: pre;
            overflow-x: auto;
        }
        .line-row {
            margin: 0 !important;
            padding: 1px 0 !important;
            min-height: 1.4em;
        }
        .highlight-add {
            background-color: rgba(46, 160, 67, 0.25);
            color: #3fb950;
            display: inline-block;
            width: 100%;
        }
        .highlight-del {
            background-color: rgba(248, 51, 60, 0.25);
            color: #f85149;
            text-decoration: line-through;
            display: inline-block;
            width: 100%;
        }
    </style>
    \"\"\", unsafe_allow_html=True)

    # Interactive Navigation Action Buttons using Native Streamlit Columns
    col1, col2, col3, col4 = st.columns(4)
    
    # Initialize Streamlit active view tracker state
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

    # Select display data based on active tracking state
    if st.session_state.current_view == "Show All":
        selected_data = "".join(all_rows)
    elif st.session_state.current_view == "Added":
        selected_data = "".join(added_rows) if added_rows else '<div class="line-row">No records found.</div>'
    elif st.session_state.current_view == "Deleted":
        selected_data = "".join(deleted_rows) if deleted_rows else '<div class="line-row">No records found.</div>'
    elif st.session_state.current_view == "Modified":
        selected_data = "".join(modified_rows) if modified_rows else '<div class="line-row">No records found.</div>'

    st.subheader(f"Viewing: {st.session_state.current_view}")
    
    # Render final zero-spacing absolute-font diff layout matrix 
    st.markdown(f'<div class="diff-container">{selected_data}</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
"""

# 2. Define standard external python requirements needed for Streamlit environment engine
requirements_content = """streamlit>=1.35.0
"""

# 3. Streamlit internal server theme setup to guarantee a Dark Mode default experience
config_toml_content = """[theme]
primaryColor = "#1f6feb"
backgroundColor = "#0d1117"
secondaryBackgroundColor = "#161b22"
textColor = "#c9d1d9"
font = "monospace"
"""

print("Initializing local setup deployment for Streamlit architecture...")

# Write Streamlit target runtime file
with open("app.py", "w", encoding="utf-8") as f:
    f.write(app_script_content)
print("[SUCCESS] Generated file: app.py")

# Write environment specification file
with open("requirements.txt", "w", encoding="utf-8") as f:
    f.write(requirements_content)
print("[SUCCESS] Generated file: requirements.txt")

# Build target subfolder hidden settings layout configurations
os.makedirs(".streamlit", exist_ok=True)
with open(".streamlit/config.toml", "w", encoding="utf-8") as f:
    f.write(config_toml_content)
print("[SUCCESS] Generated configuration setup: .streamlit/config.toml")

print("\\nInitialization Complete! To run locally, execute: pip install -r requirements.txt && streamlit run app.py")
