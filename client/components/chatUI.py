import streamlit as st
from utils.api import ask_question_function

def render_chat():
    st.subheader("chat with your assistant")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    #render existing chat history
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).markdown(msg["content"])


    #input and response to backend api
    user_input = st.chat_input("type your question....")

    if user_input:
        st.chat_message("user").markdown(user_input)
        st.session_state.messages.append({"role":"user","content": user_input})

        response = ask_question_function(user_input)

        if response.status_code == 200:
            data = response.json()
            answer = data["response"]
            sources = data.get("sources",[])
            st.chat_message("assistant").markdown(answer)
            if sources:
                st.markdown(" **Sources: **")
                for src in sources:
                    st.markdown(f"- '{src}'")

            st.session_state.messages.append({"role":"assistant","content":answer})
        else:
            st.error(f"Error: {response.text}")