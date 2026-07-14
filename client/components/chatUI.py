import streamlit as st
from utils.api import ask_question_function

AVATARS = {"user": "🙋", "assistant": "🩺"}


def _render_sources(sources):
    if not sources:
        return
    with st.expander(f"📎 Sources ({len(sources)})"):
        for src in sources:
            if isinstance(src, dict):
                document = src.get("document", "Uploaded document")
                page = src.get("page")
                snippet = src.get("snippet", "")
                page_text = f" · page {page}" if page else ""
                st.markdown(f"**{document}{page_text}**")
                if snippet:
                    st.caption(snippet)
                st.divider()
            else:
                st.markdown(f"- {src}")


def render_chat():
    st.subheader("💬 Chat with your assistant")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if not st.session_state.messages:
        st.info("Upload a clinical protocol PDF from the sidebar, then ask a question to get started.")

    # render existing chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar=AVATARS.get(msg["role"])):
            st.markdown(msg["content"])
            _render_sources(msg.get("sources"))

    # input and response to backend api
    user_input = st.chat_input("Type your question...")

    if user_input:
        st.chat_message("user", avatar=AVATARS["user"]).markdown(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.chat_message("assistant", avatar=AVATARS["assistant"]):
            with st.spinner("Reviewing the documents..."):
                response = ask_question_function(user_input)

            if response.status_code == 200:
                data = response.json()
                answer = data["response"]
                sources = data.get("sources", [])
                st.markdown(answer)
                _render_sources(sources)
                st.session_state.messages.append(
                    {"role": "assistant", "content": answer, "sources": sources}
                )
            else:
                error_text = f"Error: {response.text}"
                st.error(error_text)
                st.session_state.messages.append({"role": "assistant", "content": error_text})
