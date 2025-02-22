import streamlit as st

# Import de cada submódulo
from .auth import login
from .logs_manager import monitoramento
from .scripts_manager import (
    executar_scripts,
    configurar_scripts
)
from .constants import LOG_DIRECTORY
from .scheduler_manager import is_scheduler_running
from knowledge_manager import main as knowledge_main
from chat.chat_app import main as chat_main
from app.variavel_du import var_du as variavel_du

def main():
    st.sidebar.title("Navegação")
    if "authenticated" in st.session_state and st.session_state["authenticated"]:
        if st.sidebar.button("Logout"):
            st.session_state["authenticated"] = False
            st.session_state["user_email"] = ""
            st.session_state["user_apelido"] = ""
            st.rerun()

        st.success(f"Bem-vindo, {st.session_state.get('user_apelido', '')}!")

        option = st.sidebar.radio(
            "Escolha a página",
            ("Chat", "Gerenciar Conhecimento", "Executar Scripts", "Configurar Scripts", "Monitoramento", "Variável D.U.")
        )

        if option == "Chat":
            chat_main()


        elif option == "Gerenciar Conhecimento":
            knowledge_main()
        elif option == "Executar Scripts":
            executar_scripts()
        elif option == "Configurar Scripts":
            configurar_scripts()
        elif option == "Monitoramento":
            monitoramento()
        elif option == "Variável D.U.":
            variavel_du()
    else:
        login()

# Caso alguém rode este arquivo diretamente (ex.: python -m app.main_app)
if __name__ == "__main__":
    main()