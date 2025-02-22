import streamlit as st

from .loaders import load_csv, load_instructions
from .core import generate_response

def main():
    st.title("Atendente Comercial")

    # Exemplo: pega username (ou já vem via login)
    if "username" not in st.session_state:
        st.session_state.username = "Admin"

    instructions_df = load_instructions()
    knowledge_base_df = load_csv()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Exibe histórico anterior
    for msg in st.session_state.messages:
        if msg["role"]=="user":
            st.chat_message("user").write(msg["content"])
        else:
            st.chat_message("assistant").write(msg["content"])

    user_input = st.chat_input("Digite sua pergunta aqui...")
    if user_input:
        st.session_state.messages.append({"role":"user","content":user_input})
        st.chat_message("user").write(user_input)

        response = generate_response(user_input, knowledge_base_df, instructions_df)

        st.session_state.messages.append({"role":"assistant","content":response})
        st.chat_message("assistant").markdown(response)

if __name__=="__main__":
    main()
