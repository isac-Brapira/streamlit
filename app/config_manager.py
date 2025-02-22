import os
import json
import streamlit as st
import time
from .constants import (
    CONFIG_FILE,
    SCHEDULE_FILE,
    ROTINAS_DISPONIVEIS
)

def carregar_configuracoes():
    """Lê o rotinas_config.json com as rotinas ativas/inativas."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                content = f.read().strip()
                if not content:  # Verifica se o arquivo está vazio
                    raise ValueError("Arquivo JSON está vazio.")
                return json.loads(content)
        except (json.JSONDecodeError, ValueError) as e:
            st.error(f"Erro ao carregar o arquivo de configurações: {e}")
            # Cria um arquivo de configuração padrão vazio
            configuracoes_padrao = {rotina[1]: False for rotina in ROTINAS_DISPONIVEIS}
            salvar_configuracoes(configuracoes_padrao)
            return configuracoes_padrao
    else:
        # Se o arquivo não existe, cria um padrão vazio
        configuracoes_padrao = {rotina[1]: False for rotina in ROTINAS_DISPONIVEIS}
        salvar_configuracoes(configuracoes_padrao)
        return configuracoes_padrao

def salvar_configuracoes(config):
    """Salva as rotinas ativas/inativas em rotinas_config.json."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def carregar_horario():
    """
    Lê o schedule_config.json, que pode conter:
      {
        "ativo": bool,
        "horario": "HH:MM",
        "horarios_criticas_rn": [...],
        "horario_gc": "HH:MM",
        "tarefas": [...],
        "ultima_modificacao": "...",
        ...
      }
    """
    if os.path.exists(SCHEDULE_FILE):
        try:
            with open(SCHEDULE_FILE, "r") as f:
                content = f.read().strip()
                if not content:
                    raise ValueError("Arquivo JSON está vazio.")
                return json.loads(content)
        except (json.JSONDecodeError, ValueError) as e:
            st.error(f"Erro ao carregar o arquivo de agendamento: {e}")
            config_padrao = {
                "ativo": False,
                "horario": "",
                "horario_faturamento": "",
                "horarios_criticas_rn": [],
                "horario_gc": "",
                "tarefas": [],
                "ultima_modificacao": ""
            }
            salvar_horario(config_padrao)
            return config_padrao
    else:
        config_padrao = {
            "ativo": False,
            "horario": "",
            "horario_faturamento": "",
            "horarios_criticas_rn": [],
            "horario_gc": "",
            "tarefas": [],
            "ultima_modificacao": ""
        }
        salvar_horario(config_padrao)
        return config_padrao

def salvar_horario(config):
    """
    Salva no schedule_config.json.
    Atualiza 'ultima_modificacao' para o timestamp atual para forçar
    o scheduler a detectar a mudança.
    """
    config["ultima_modificacao"] = str(time.time())
    with open(SCHEDULE_FILE, "w") as f:
        json.dump(config, f, indent=4)

def aplicar_override_config(override: dict) -> dict:
    """
    Aplica overrides no rotinas_config.json e retorna o dicionário anterior (backup).
    """
    from .constants import CONFIG_FILE
    import json
    
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        original = json.load(f)
    backup = dict(original)

    if override is not None:
        if "__all__" in override:
            set_all = override["__all__"]
            for k in backup.keys():
                backup[k] = bool(set_all)
            del override["__all__"]

        for k, v in override.items():
            backup[k] = v

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(backup, f, indent=4)

    return original


def restaurar_config(config_anterior: dict):
    """Restaura a configuração original no rotinas_config.json."""
    from .constants import CONFIG_FILE
    import json

    if config_anterior is None:
        return
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_anterior, f, indent=4)