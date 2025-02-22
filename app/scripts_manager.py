import os
import json
import sys
import streamlit as st
import subprocess
from .constants import CONFIG_FILE
from functions.plan_gc import atualizar_plan_gc
from functions.plan_faturamento import atualizar_faturamento
from functions.fechamento_d0 import executar_fechamento_d0

from .config_manager import (
    carregar_configuracoes,
    salvar_configuracoes,
    carregar_horario,
    salvar_horario,
    ROTINAS_DISPONIVEIS
)
from .scheduler_manager import (
    iniciar_intermediador,
    parar_intermediador
)

def executar_scripts():
    """
    Página do Streamlit para executar scripts manualmente.
    """
    st.title("Executar Scripts")
    st.write("Escolha um script para executar:")

    scripts = {
        "Atualizar relatórios do Promax": "main",
        "Críticas RN": "030111",
        "Atualizar Plan GC": "atualizar_plan_gc",
        "Atualizar Faturamento": "atualizar_faturamento",
        "Fechamento D-0": "fechamento_d0"
    }

    script_selecionado = st.selectbox("Selecione o script", list(scripts.keys()))

    if st.button("Executar"):
        process = None
        log_lines = []
        backup_config = None

        # 1) SE FOR "Atualizar Plan GC"
        if scripts[script_selecionado] == "atualizar_plan_gc":
            st.info("Executando atualização da planilha...")
            atualizar_plan_gc()
            return
        
        # 2) SE FOR "Atualizar Faturamento"
        if scripts[script_selecionado] == "atualizar_faturamento":
            st.info("Executando atualização da planilha...")
            atualizar_faturamento()
            return

        # 3) SE FOR "Fechamento D-0"
        if scripts[script_selecionado] == "fechamento_d0":
            st.info("Executando Fechamento D-0...")
            executar_fechamento_d0()
            return

        # 4) DEMAIS SCRIPTS (Promax, Críticas RN, etc.)
        try:
            st.info("Executando o script...")
            log_area = st.empty()

            with st.spinner("Executando o script..."):
                env = os.environ.copy()
                env["PYTHONIOENCODING"] = "utf-8"

                script_to_run = os.path.abspath(
                    r"\\192.168.1.213\Administrativo\TecInfo\Automacoes\Guilherme\Promax\main.py"
                )

                # Faz backup do config atual para depois restaurar
                with open(CONFIG_FILE, "r") as f:
                    backup_config = json.load(f)

                if scripts[script_selecionado] == "030111":
                    # Override do config para rodar apenas "Críticas RN"
                    config_override = {key: False for key in backup_config.keys()}
                    config_override["030111"] = True
                    with open(CONFIG_FILE, "w") as f:
                        json.dump(config_override, f, indent=4)

                process = subprocess.Popen(
                    [sys.executable, "-u", script_to_run],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
                )

                while True:
                    output = process.stdout.readline()
                    if output == b"" and process.poll() is not None:
                        break
                    if output:
                        decoded_output = output.decode('utf-8', errors='replace').strip()
                        log_lines.append(decoded_output)
                        log_area.text("\n".join(log_lines))

                stderr = process.stderr.read()
                if stderr.strip():
                    decoded_error = stderr.decode('utf-8', errors='replace')
                    log_lines.append(f"\n[ERRO] {decoded_error.strip()}")
                    log_area.text("\n".join(log_lines))
                    st.error("Erros encontrados durante a execução.")

                if process.returncode == 0:
                    st.success("Script executado com sucesso!")
                else:
                    st.error(f"O script terminou com erro. Código de saída: {process.returncode}")

        except Exception as e:
            st.error(f"Erro ao executar o script: {e}")
        finally:
            # Restaura config se foi modificado
            if backup_config:
                with open(CONFIG_FILE, "w") as f:
                    json.dump(backup_config, f, indent=4)
                st.info("Configurações padrão restauradas.")

            # Se estiver ainda rodando, finaliza
            if process and process.poll() is None:
                process.terminate()
                process.wait()

            log_lines.append("\nExecução finalizada.")
            if 'log_area' in locals():
                log_area.text("\n".join(log_lines))

def configurar_scripts():
    """Página do Streamlit para configurar rotinas e o agendador."""
    st.title("Configurar Scripts")
    st.write("\n**Programador de Execução:**")

    config_horario = carregar_horario()
    programador_ativo = st.checkbox("Ativar Programador", value=config_horario.get("ativo", False))

    horarios_criticas_rn = config_horario.get("horarios_criticas_rn", "")
    horario_faturamento = config_horario.get("horario_faturamento", "")
    horario_gc = config_horario.get("horario_gc", "")

    if programador_ativo:
        horario = st.text_input("Informe o horário para o script principal (HH:MM):",
                                value=config_horario.get("horario", ""))
        if horario and len(horario.split(":")) == 2:
            try:
                hora, minuto = map(int, horario.split(":"))
                if 0 <= hora < 24 and 0 <= minuto < 60:
                    config_horario["horario"] = horario
                else:
                    st.error("Horário inválido. Use o formato HH:MM.")
            except ValueError:
                st.error("Horário inválido. Use o formato HH:MM.")
        else:
            config_horario["horario"] = ""

        # Campo adicional para os horários de "Críticas RN"
        horarios_criticas_rn = st.text_input(
            "Informe os horários para 'Críticas RN' separados por vírgula (ex: 09:00, 13:30, 17:00):",
            value=", ".join(horarios_criticas_rn) if isinstance(horarios_criticas_rn, list) else horarios_criticas_rn
        )
        try:
            horarios_criticas_rn_list = [h.strip() for h in horarios_criticas_rn.split(",") if h.strip()]
            for h in horarios_criticas_rn_list:
                hh, mm = map(int, h.split(":"))
                if not (0 <= hh < 24 and 0 <= mm < 60):
                    raise ValueError(f"Horário inválido: {h}")
            config_horario["horarios_criticas_rn"] = horarios_criticas_rn_list
        except ValueError as e:
            st.error(f"Erro ao processar os horários de 'Críticas RN': {e}")
            horarios_criticas_rn_list = []

        # Campo para o horário da atualização da planilha GC
        horario_gc = st.text_input("Informe o horário para atualização da planilha GC (HH:MM):", value=horario_gc)
        if horario_gc and len(horario_gc.split(":")) == 2:
            try:
                hora_gc, minuto_gc = map(int, horario_gc.split(":"))
                if 0 <= hora_gc < 24 and 0 <= minuto_gc < 60:
                    config_horario["horario_gc"] = horario_gc
                else:
                    st.error("Horário inválido. Use o formato HH:MM.")
            except ValueError:
                st.error("Horário inválido. Use o formato HH:MM.")
        else:
            config_horario["horario_gc"] = ""

        # Campo para o horário da atualização do Faturamento
        horario_faturamento = st.text_input("Informe o horário para atualização do Faturamento mensal (HH:MM):", value=horario_faturamento)
        if horario_faturamento and len(horario_faturamento.split(":")) == 2:
            try:
                hora_fat, minuto_fat = map(int, horario_faturamento.split(":"))
                if 0 <= hora_fat < 24 and 0 <= minuto_fat < 60:
                    config_horario["horario_faturamento"] = horario_faturamento
                else:
                    st.error("Horário inválido. Use o formato HH:MM.")
            except ValueError:
                st.error("Horário inválido. Use o formato HH:MM.")
        else:
            config_horario["horario_faturamento"] = ""

        # Constrói lista de tarefas
        novas_tarefas = []
        if config_horario["horario"]:
            novas_tarefas.append({
                "nome": "principal",
                "horarios": [config_horario["horario"]]
            })
        if config_horario["horarios_criticas_rn"]:
            novas_tarefas.append({
                "nome": "criticas_rn",
                "horarios": config_horario["horarios_criticas_rn"]
            })
        if config_horario["horario_gc"]:
            novas_tarefas.append({
                "nome": "atualizar_plan_gc",
                "horarios": config_horario["horario_gc"]
            })
        if config_horario["horario_faturamento"]:
            novas_tarefas.append({
                "nome": "atualizar_faturamento",
                "horarios": config_horario["horario_faturamento"]
            })

        config_horario["tarefas"] = novas_tarefas
    else:
        config_horario["tarefas"] = []

    st.write("\nSelecione as rotinas que deseja ativar/desativar:")
    configuracoes = carregar_configuracoes()

    for nome_rotina, codigo_rotina in ROTINAS_DISPONIVEIS:
        configuracoes[codigo_rotina] = st.checkbox(nome_rotina, value=configuracoes[codigo_rotina])

    if st.button("Salvar Configurações"):
        salvar_configuracoes(configuracoes)
        config_horario["ativo"] = programador_ativo
        salvar_horario(config_horario)

        if programador_ativo:
            from .scheduler_manager import iniciar_intermediador
            iniciar_intermediador()
        else:
            from .scheduler_manager import parar_intermediador
            parar_intermediador()

        st.success("Configurações salvas com sucesso!")
