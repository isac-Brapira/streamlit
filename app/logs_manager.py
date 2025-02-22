# app/logs_manager.py
import os
import time
import streamlit as st
from .constants import LOG_DIRECTORY

def registrar_log(nome_arquivo: str, mensagem: str):
    """Registra mensagens no arquivo de log com timestamp."""
    from datetime import datetime
    caminho_log = os.path.join(LOG_DIRECTORY, nome_arquivo)
    with open(caminho_log, "a", encoding="utf-8") as log_file:
        log_file.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {mensagem}\n")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {mensagem}")

def listar_logs_disponiveis():
    """Lista os arquivos de log disponíveis no diretório de logs."""
    if os.path.exists(LOG_DIRECTORY):
        return [f for f in os.listdir(LOG_DIRECTORY) if f.endswith(".log")]
    else:
        return []

def ler_log_em_tempo_real(arquivo_log):
    """Lê e exibe um arquivo de log em tempo real no Streamlit."""
    st.subheader(f"Monitorando: {arquivo_log}")
    caminho_arquivo = os.path.join(LOG_DIRECTORY, arquivo_log)

    if not os.path.exists(caminho_arquivo):
        st.error(f"Arquivo de log não encontrado: {arquivo_log}")
        return

    with open(caminho_arquivo, "r") as f:
        st.info("Carregando log...")
        placeholder = st.empty()

        while True:
            where = f.tell()
            line = f.readline()
            if not line:
                time.sleep(1)
                f.seek(where)
            else:
                placeholder.text(line.strip())

def monitoramento():
    """Página de monitoramento no Streamlit."""
    st.title("Monitoramento de Logs")
    st.write("Acompanhe os logs dos processos em execução.")

    arquivos_logs = listar_logs_disponiveis()

    if not arquivos_logs:
        st.warning("Nenhum arquivo de log encontrado.")
        return

    log_selecionado = st.selectbox("Selecione um log para monitorar", arquivos_logs)

    if st.button("Iniciar Monitoramento"):
        ler_log_em_tempo_real(log_selecionado)
