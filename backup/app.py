import streamlit as st
import json
import os
import subprocess
import psutil
import bcrypt
from db.database import connect_db
import sys
import time  # <--- Import para gerar timestamp de ultima_modificacao
from chat.chat_app import main as chat_main

CONFIG_FILE = "rotinas_config.json"
SCHEDULE_FILE = "schedule_config.json"
SCHEDULER_SCRIPT = "scheduler_intermediador.py"

LOG_DIRECTORY = r"\\192.168.1.213\Arquivos\Administrativo\TecInfo\DESENVOLVIMENTOS\atendente-IA-v1\Logs"

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


# Arquivo onde guardamos o PID do scheduler_intermediador.py
PIDFILE_NAME = "scheduler_pid.txt"

ROTINAS_DISPONIVEIS = [
    ("Visitas do Vendedor", "012011"),
    ("Relatório do Cliente", "0105070402"),
    ("Compras por Fornecedor", "020512"),
    ("Grade", "020304"),
    ("Críticas RN", "030111"),
    ("Buffer", "03012601"),
    ("Notas Fiscais", "030237"),
    ("Vendas Mês Caixa", "030509"),
    ("Vendas Mês Hecto", "030509"),
    ("Critica D-0 CX", "03013604"),
    ("Crítica D-0 HL", "03013604"),
    ("Relatório de Pedidos", "03014701"),
    ("Monitoramento Parceiro Ambev", "03014606"),
    ("Vendas no Ano", "0512"),
    ("Lançamentos Detalhados OBZ", "150501"),
]



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
        "horario": "HH:MM",           # para script principal
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
                if not content:  # Verifica se o arquivo está vazio
                    raise ValueError("Arquivo JSON está vazio.")
                return json.loads(content)
        except (json.JSONDecodeError, ValueError) as e:
            st.error(f"Erro ao carregar o arquivo de agendamento: {e}")
            # Cria um arquivo de agendamento padrão vazio
            config_padrao = {
                "ativo": False,
                "horario": "",
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
            CREATE_NEW_CONSOLE = 0x00000010
            creationflags = CREATE_NEW_CONSOLE

            process = subprocess.Popen(
                [sys.executable, scheduler_path],
                creationflags=creationflags,
                close_fds=True,
                cwd=os.path.dirname(scheduler_path),
            )
        else:
            # Linux/macOS
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


def configurar_scripts():
    """Página do Streamlit para configurar rotinas e o agendador."""
    st.title("Configurar Scripts")
    st.write("\n**Programador de Execução:**")

    config_horario = carregar_horario()
    programador_ativo = st.checkbox("Ativar Programador", value=config_horario.get("ativo", False))

    horarios_criticas_rn = config_horario.get("horarios_criticas_rn", "")
    horario_gc = config_horario.get("horario_gc", "")

    if programador_ativo:
        # Campo para o horário padrão do programador (script principal)
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
            # Se o campo ficou vazio ou inválido, pode apagar config_horario["horario"]
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
        horario_gc = st.text_input(
            "Informe o horário para atualização da planilha GC (HH:MM):",
            value=horario_gc
        )
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

        # --- NOVO: Construir a lista "tarefas" ---
        novas_tarefas = []

        # Tarefa "principal"
        if config_horario["horario"]:
            novas_tarefas.append({
                "nome": "principal",
                "horarios": [config_horario["horario"]]
            })

        # Tarefa "criticas_rn"
        if config_horario["horarios_criticas_rn"]:
            novas_tarefas.append({
                "nome": "criticas_rn",
                "horarios": config_horario["horarios_criticas_rn"]
            })

        # Exemplo: se quisermos mapear "horario_gc" para alguma tarefa "gc_planilha", 
        # poderíamos adicionar:
        # if config_horario["horario_gc"]:
        #     novas_tarefas.append({
        #         "nome": "gc_planilha",
        #         "horarios": [config_horario["horario_gc"]]
        #     })

        config_horario["tarefas"] = novas_tarefas

    else:
        # Se não estiver ativo, podemos limpar "tarefas" ou deixá-las lá
        # Mas normalmente zeramos a lista para não manter agendamentos
        config_horario["tarefas"] = []

    # Seção de rotinas ativas/inativas
    st.write("\nSelecione as rotinas que deseja ativar/desativar:")
    configuracoes = carregar_configuracoes()

    for nome_rotina, codigo_rotina in ROTINAS_DISPONIVEIS:
        configuracoes[codigo_rotina] = st.checkbox(nome_rotina, value=configuracoes[codigo_rotina])

    if st.button("Salvar Configurações"):
        # Salva rotinas_config.json
        salvar_configuracoes(configuracoes)

        # Ajusta 'ativo' e salva schedule_config.json com ultima_modificacao
        config_horario["ativo"] = programador_ativo
        salvar_horario(config_horario)

        # Se programador estiver ativo, inicia ou atualiza o intermediador; senão, encerra
        if programador_ativo:
            iniciar_intermediador()
        else:
            parar_intermediador()

        st.success("Configurações salvas com sucesso!")


def executar_scripts():
    """
    Página do Streamlit para executar scripts manualmente.
    """
    st.title("Executar Scripts")
    st.write("Escolha um script para executar:")

    scripts = {
        "Atualizar relatórios do Promax": "main",
        "Críticas RN": "030111",
        "Atualizar Plan GC": "atualizar_plan_gc"
    }

    script_selecionado = st.selectbox("Selecione o script", list(scripts.keys()))

    if st.button("Executar"):
        process = None
        log_lines = []
        backup_config = None

        if scripts[script_selecionado] == "atualizar_plan_gc":
            st.info("Executando atualização da planilha...")
            atualizar_plan_gc()
            return

        try:
            st.info("Executando o script...")
            log_area = st.empty()

            with st.spinner("Executando o script..."):
                env = os.environ.copy()
                env["PYTHONIOENCODING"] = "utf-8"

                # Define o caminho correto do script a ser executado
                script_to_run = os.path.abspath(
                    r"\\192.168.1.213\Administrativo\TecInfo\Automacoes\Guilherme\Promax\main.py"
                )

                # Fazer backup das configurações antes de qualquer alteração
                with open(CONFIG_FILE, "r") as f:
                    backup_config = json.load(f)

                # Configuração específica para "Críticas RN"
                if scripts[script_selecionado] == "030111":
                    config_override = {key: False for key in backup_config.keys()}
                    config_override["030111"] = True

                    with open(CONFIG_FILE, "w") as f:
                        json.dump(config_override, f, indent=4)

                process = subprocess.Popen(
                    [
                        sys.executable,
                        "-u",
                        script_to_run
                    ],
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
            # Restaurar as configurações originais
            if backup_config:
                with open(CONFIG_FILE, "w") as f:
                    json.dump(backup_config, f, indent=4)
                st.info("Configurações padrão restauradas.")

            # Garantir que o processo é encerrado adequadamente
            if process and process.poll() is None:
                process.terminate()
                process.wait()

            log_lines.append("\nExecução finalizada.")
            if 'log_area' in locals():
                log_area.text("\n".join(log_lines))

def atualizar_plan_gc():
    """
    Atualiza a planilha Excel 'ACOMP_VOL_2025.xlsb' localizada na rede e exibe o progresso no Streamlit.
    """
    import win32com.client as win32
    import pythoncom
    import os
    import streamlit as st

    try:
        # Caminho da planilha na rede
        caminho_planilha = r"\\192.168.1.213\Arquivos\PEX\SPO - Pilar Comercial\2025\Gestão Comercial\ACOMP_VOL_2025.xlsb"

        st.write("Iniciando o processo de atualização da planilha...")
        
        # Verifica se o arquivo existe
        if not os.path.exists(caminho_planilha):
            raise FileNotFoundError(f"Arquivo não encontrado: {caminho_planilha}")
        st.write("Caminho verificado: o arquivo existe.")

        # Inicializa o Excel no modo invisível
        pythoncom.CoInitialize()  # Garante que o COM esteja inicializado
        excel = win32.DispatchEx("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False  # Desativa alertas e janelas
        excel.AskToUpdateLinks = False
        st.write("Excel inicializado no modo invisível.")

        # Abre a planilha
        try:
            workbook = excel.Workbooks.Open(caminho_planilha, UpdateLinks=0)
            st.write("Planilha aberta com sucesso.")
        except Exception as e:
            raise RuntimeError(f"Erro ao abrir a planilha: {e}")

        st.write("Atualizando conexões de dados...")
        workbook.RefreshAll()
        
        st.write("Aguardando a conclusão das atualizações...")
        excel.CalculateUntilAsyncQueriesDone()
        st.write("Atualização concluída com sucesso.")

        st.write("Salvando as alterações na planilha...")
        try:
            workbook.Save()
            workbook.Close(SaveChanges=True)
            st.write("Planilha salva e fechada com sucesso.")
        except Exception as e:
            raise RuntimeError(f"Erro ao salvar a planilha: {e}")

        st.write("Encerrando o Excel...")
        excel.Quit()
        pythoncom.CoUninitialize()
        st.success("Atualização da planilha concluída com sucesso!")

    except FileNotFoundError as e:
        st.error(f"Erro: {e}")

    except RuntimeError as e:
        st.error(f"Erro ao atualizar a planilha: {e}")

    except Exception as e:
        # Garante que o Excel seja encerrado mesmo em caso de erro
        try:
            excel.Quit()
            pythoncom.CoUninitialize()
        except:
            pass
        st.error(f"Erro inesperado ao atualizar a planilha: {e}")

    finally:
        # Garante que o Excel é encerrado, mesmo em caso de erro
        try:
            excel.Quit()
        except:
            pass


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


def main():
    st.sidebar.title("Navegação")
    if "authenticated" in st.session_state and st.session_state["authenticated"]:
        if st.sidebar.button("Logout"):
            st.session_state["authenticated"] = False
            st.session_state["user_email"] = ""
            st.session_state["user_apelido"] = ""
            st.rerun()

        st.success("Bem-vindo, " + st.session_state["user_apelido"] + "!")

        option = st.sidebar.radio(
            "Escolha a página",
            ("Chat", "Gerenciar Conhecimento", "Executar Scripts", "Configurar Scripts", "Monitoramento")
        )

        if option == "Chat":
            import chat
            chat.main()
        elif option == "Gerenciar Conhecimento":
            import knowledge_manager
            knowledge_manager.main()
        elif option == "Executar Scripts":
            executar_scripts()
        elif option == "Configurar Scripts":
            configurar_scripts()
        elif option == "Monitoramento":
            monitoramento()
    else:
        login()


if __name__ == "__main__":
    main()
