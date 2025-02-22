import bcrypt
import streamlit as st
from db.database import connect_db

def login():
    st.title("Login")
    email = st.text_input("E-mail")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        conn = connect_db()
        if conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT apelido, senha FROM usuarios WHERE email = %s", (email,))
                user = cursor.fetchone()
                conn.close()

                if user:
                    apelido, db_hashed_password = user
                    if bcrypt.checkpw(senha.encode('utf-8'), db_hashed_password.encode('utf-8')):
                        st.session_state["authenticated"] = True
                        st.session_state["user_email"] = email
                        st.session_state["user_apelido"] = apelido
                        st.success(f"Bem-vindo, {apelido}!")
                        st.rerun()
                    else:
                        st.error("Senha incorreta!")
                else:
                    st.error("Usuário não encontrado!")
        else:
            st.error("Erro ao conectar ao banco de dados.")
