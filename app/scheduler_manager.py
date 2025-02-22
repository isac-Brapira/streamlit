# app/scheduler_manager.py

import os
import sys
import psutil
import streamlit as st
import subprocess  # <-- Importar aqui, no escopo global!
from .constants import SCHEDULER_SCRIPT, PIDFILE_NAME
from .config_manager import salvar_horario, carregar_horario
import time

def get_pidfile_path():
    """Retorna o caminho absoluto do arquivo de PID (scheduler_pid.txt)."""
    scheduler_path = os.path.abspath(SCHEDULER_SCRIPT)
    base_dir = os.path.dirname(scheduler_path)
    return os.path.join(base_dir, PIDFILE_NAME)

def is_scheduler_running():
    """Verifica se o agendador está rodando (processo vivo pelo PID)."""
    pidfile_path = get_pidfile_path()
    if not os.path.exists(pidfile_path):
        return False
    try:
        with open(pidfile_path, 'r') as f:
            pid_str = f.read().strip()
        pid = int(pid_str)
        proc = psutil.Process(pid)
        return proc.is_running()
    except:
        return False

def iniciar_intermediador():
    """Inicia o script intermediador em nova janela no Windows (CREATE_NEW_CONSOLE)."""
    if is_scheduler_running():
        st.info("Intermediador já está em execução.")
        return

    try:
        scheduler_path = os.path.abspath(SCHEDULER_SCRIPT)

        if os.name == 'nt':
            # Definição da flag CREATE_NEW_CONSOLE no Windows
            CREATE_NEW_CONSOLE = 0x00000010
            process = subprocess.Popen(
                [sys.executable, scheduler_path],
                creationflags=CREATE_NEW_CONSOLE,
                close_fds=True,
                cwd=os.path.dirname(scheduler_path),
            )
        else:
            # Em Linux/macOS
            process = subprocess.Popen(
                [sys.executable, scheduler_path],
                start_new_session=True,
                close_fds=True,
                cwd=os.path.dirname(scheduler_path),
            )

        pid = process.pid
        pidfile_path = get_pidfile_path()
        with open(pidfile_path, 'w') as f:
            f.write(str(pid))

        st.success(f"Intermediador iniciado com sucesso! PID={pid}")

    except Exception as e:
        st.error(f"Erro ao iniciar o intermediador: {e}")

def parar_intermediador():
    """Encerra o script intermediador (mata o processo pelo PID salvo)."""
    pidfile_path = get_pidfile_path()
    if not os.path.exists(pidfile_path):
        st.warning("Nenhum PID salvo. Intermediador provavelmente não está rodando.")
        return

    try:
        with open(pidfile_path, 'r') as f:
            pid_str = f.read().strip()
        pid = int(pid_str)
        proc = psutil.Process(pid)
        proc.terminate()
        proc.wait(timeout=5)

        os.remove(pidfile_path)
        st.success("Intermediador encerrado com sucesso!")
    except psutil.NoSuchProcess:
        st.warning("O processo não estava mais em execução.")
        if os.path.exists(pidfile_path):
            os.remove(pidfile_path)
    except Exception as e:
        st.error(f"Erro ao parar o intermediador: {e}")
