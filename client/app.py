import streamlit as st
from components.upload import render_uploader
from components.history_download import render_history_download

from components.chatUI import render_chat

st.set_page_config(page_title="Clinical Protocol Assistant", page_icon="🩺", layout="wide")

st.title("🩺 Clinical Protocol Assistant")
st.caption("Ask questions about your uploaded clinical protocol documents.")

render_uploader()
render_history_download()

render_chat()