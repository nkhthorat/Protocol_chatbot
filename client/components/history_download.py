import streamlit as st

def render_history_download():
    if st.session_state.get("messages"):
        chat_text = "\n\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in st.session_state.messages
        )
        st.sidebar.divider()
        st.sidebar.download_button(
            "⬇️ Download chat history",
            chat_text,
            file_name="chat_history.txt",
            mime="text/plain",
            use_container_width=True,
        )