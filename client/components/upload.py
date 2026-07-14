import streamlit as st
from utils.api import upload_pdfs_api


def render_uploader():
    st.sidebar.header("📄 Upload Medical Documents")
    uploaded_files = st.sidebar.file_uploader(
        "Upload one or more PDFs", type="pdf", accept_multiple_files=True
    )
    if uploaded_files:
        for f in uploaded_files:
            st.sidebar.caption(f"• {f.name} ({f.size / 1024:.0f} KB)")

    if st.sidebar.button("Upload to knowledge base", use_container_width=True) and uploaded_files:
        with st.sidebar.status("Embedding documents... this can take a few minutes for large PDFs.", expanded=False) as status:
            response = upload_pdfs_api(uploaded_files)
            if response.status_code == 200:
                status.update(label="Uploaded successfully ✅", state="complete")
            else:
                status.update(label="Upload failed ❌", state="error")
                st.sidebar.error(f"Error: {response.text}")