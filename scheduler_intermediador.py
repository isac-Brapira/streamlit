import os
import sys
import json
import subprocess
import schedule
import time
from datetime import datetime
from typing import Dict, Any
import threading
import traceback

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIRECTORY = os.path.join(BASE_DIR, "logs")
SCHEDULE_FILE = os.path.join(BASE_DIR, "schedule_config.json")
CONFIG_FILE = os.path.join(BASE_DIR, "rotinas_config.json")

os.makedirs(LOG_DIRECTORY, exist_ok=True)

# Tempo mínimo entre execuções (em segundos)
INTERVALO_MINIMO = 30
# Dicionário que manterá o "momento" da última execução de cada tarefa
ultima_execucao_ts: Dict[str, float] = {}

###############################################################################
# Funções de Log e Config
###############################################################################
def registrar_log(nome_arquivo: str, mensagem: str):
    """Registra mensagens no arquivo de log com timestamp e printa no console."""
    caminho_log = os.path.join(LOG_DIRECTORY, nome_arquivo)
    data_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg_completa = f"[{data_str}] {mensagem}"
    with open(caminho_log, "a", encoding="utf-8") as log_file:
        log_file.write(msg_completa + "\n")
    print(msg_completa)

def carregar_horario() -> Dict[str, Any]:
    """Lê o schedule_config.json e retorna como dicionário."""
    if os.path.exists(SCHEDULE_FILE):
        try:
            with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    raise ValueError("Arquivo JSON está vazio.")
                return json.loads(content)
        except (json.JSONDecodeError, ValueError) as e:
            registrar_log("scheduler_fatal.log", f"Erro ao carregar agendamento: {e}")
            # Retorna config padrão
            return {
                "ativo": False,
                "tarefas": [],
                "ultima_modificacao": "",
            }
    else:
        registrar_log("scheduler.log", "schedule_config.json não existe. Criando com valores padrão.")
        config_padrao = {
            "ativo": False,
            "tarefas": [],
            "ultima_modificacao": ""
        }
        with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
            json.dump(config_padrao, f, indent=4)
        return config_padrao

def imprimir_proxima_execucao():
    jobs = schedule.jobs
    if not jobs:
        registrar_log("scheduler.log", "[Scheduler] Nenhum agendamento ativo.")
        return
    for job in jobs:
        # job_func.__name__ mostrará algo como 'executar_<tarefa>'
        registrar_log("scheduler.log", 
            f"[Scheduler] -> Tarefa: {job.job_func.__name__}, Próxima execução: {job.next_run}"
        )

###############################################################################
# Dicionário de tarefas personalizadas
###############################################################################
TASKS = {
    "principal": {
        "label": "Script Principal (main.py)",
        "script": r"\\192.168.1.213\Administrativo\TecInfo\Automacoes\Guilherme\Promax\main.py",
        "override_config": None,
        "log_file": "script_principal.log",
    },
    "criticas_rn": {
        "label": "Críticas RN",
        "script": r"\\192.168.1.213\Administrativo\TecInfo\Automacoes\Guilherme\Promax\main.py",
        "override_config": {
            "__all__": False,
            "030111": True
        },
        "log_file": "criticas_rn.log",
    },
    "atualizar_faturamento": {
        "label": "Atualizar Faturamento",
        "script": r"\\192.168.1.213\Administrativo\TecInfo\DESENVOLVIMENTOS\atendente-IA-v1\functions\plan_faturamento.py",
        "override_config": None,
        "log_file": "atualizar_faturamento.log",
    },
    "atualizar_plan_gc": {
        "label": "Atualizar Planilha GC",
        "script": r"\\192.168.1.213\Administrativo\TecInfo\DESENVOLVIMENTOS\atendente-IA-v1\functions\plan_gc.py",
        "override_config": None,
        "log_file": "atualizar_plan_gc.log",
    },
    # ...
}

###############################################################################
# Manipulação de Config
###############################################################################
def aplicar_override_config(override: dict):
    """Aplica uma configuração temporária no rotinas_config.json."""
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
    if config_anterior is None:
        return
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_anterior, f, indent=4)

###############################################################################
# Execução das tarefas em Thread separada
###############################################################################
def thread_executar_tarefa(nome_tarefa: str):
    """
    Roda a tarefa em background para não travar o schedule.run_pending().
    """
    try:
        executar_tarefa(nome_tarefa)
    except Exception as e:
        registrar_log("scheduler_fatal.log", 
            f"thread_executar_tarefa - Exceção ao rodar {nome_tarefa}: {e}\n{traceback.format_exc()}")

def eh_dia_valido() -> bool:
    """Exemplo: retorna True se hoje é um dia útil (segunda=0 até sábado=5)."""
    hoje = datetime.now().weekday()
    return hoje < 6

def executar_tarefa(nome_tarefa: str):
    """Executa a tarefa especificada, com override de config, logging, etc."""
    if not eh_dia_valido():
        registrar_log("scheduler.log", f"{nome_tarefa} pulado (não é dia útil).")
        return

    global ultima_execucao_ts
    agora = time.time()
    ultima_vez = ultima_execucao_ts.get(nome_tarefa, 0.0)

    if (agora - ultima_vez) < INTERVALO_MINIMO:
        registrar_log("scheduler.log", 
            f"{nome_tarefa} pulado (intervalo mínimo não respeitado).")
        return

    ultima_execucao_ts[nome_tarefa] = agora

    if nome_tarefa not in TASKS:
        registrar_log("scheduler.log", f"Tarefa '{nome_tarefa}' não definida em TASKS.")
        return

    info = TASKS[nome_tarefa]
    label = info["label"]
    script_path = info["script"]
    override = info.get("override_config")
    log_file = info["log_file"]

    registrar_log(log_file, f"[Scheduler] Iniciando {label} ...")

    config_backup = None
    try:
        if override:
            config_backup = aplicar_override_config(override)

        # Vamos ler a saída sem travar o loop do schedule
        # - Se quiser travar, pode remover a thread, mas arrisca congelar run_pending()
        proc = subprocess.Popen(
            [sys.executable, "-u", script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        caminho_log = os.path.join(LOG_DIRECTORY, log_file)

        # Em vez de bloquear lendo linha por linha, vamos ler até o fim de forma "não bloqueante"
        # Poderíamos usar select, mas algo simples é ler chunk a chunk (polling)
        while True:
            retcode = proc.poll()
            line = proc.stdout.readline()
            if line:
                line = line.rstrip("\n")
                registrar_log(log_file, line)
            if retcode is not None:
                # Processo terminou
                break
            time.sleep(0.5)

        if proc.returncode == 0:
            registrar_log(log_file, f"{label} finalizado com sucesso. [returncode=0]")
        else:
            registrar_log(log_file, f"{label} terminou com código {proc.returncode}.")

    except Exception as e:
        registrar_log(log_file, f"Erro ao executar {label}: {e}\n{traceback.format_exc()}")

    finally:
        if override:
            restaurar_config(config_backup)

def criar_funcao_agendamento(nome_tarefa: str):
    """
    Retorna uma função que chama 'thread_executar_tarefa' em background.
    """
    def _func():
        # Dispara em thread para não bloquear o schedule
        th = threading.Thread(
            target=thread_executar_tarefa, 
            args=(nome_tarefa,),
            daemon=True  # Daemon thread
        )
        th.start()
    _func.__name__ = f"executar_{nome_tarefa}"
    return _func

###############################################################################
# Atualiza Agendamentos
###############################################################################
def atualizar_agendamentos():
    config = carregar_horario()
    programador_ativo = config.get("ativo", False)
    lista_tarefas = config.get("tarefas", [])

    schedule.clear()
    registrar_log("scheduler.log", "[Scheduler] Limpando agendamentos anteriores...")

    if programador_ativo and lista_tarefas:
        for task in lista_tarefas:
            nome_tarefa = task.get("nome")
            horarios = task.get("horarios", [])

            if isinstance(horarios, str):
                horarios = [horarios]

            for h in horarios:
                if len(h.split(":")) == 2:
                    hh, mm = h.split(":")
                    try:
                        hh = int(hh)
                        mm = int(mm)
                        schedule.every().day.at(f"{hh:02d}:{mm:02d}").do(
                            criar_funcao_agendamento(nome_tarefa)
                        )
                        registrar_log("scheduler.log", 
                            f"[Scheduler] Agendando '{nome_tarefa}' para {hh:02d}:{mm:02d}")
                    except ValueError:
                        registrar_log("scheduler.log", f"[Scheduler] Horário inválido: {h}")
                else:
                    registrar_log("scheduler.log", f"[Scheduler] Formato de horário inválido: {h}")

    imprimir_proxima_execucao()

###############################################################################
# Loop Principal
###############################################################################
def monitorar_agendador():
    """
    Loop principal:
    - Verifica mudanças em schedule_config.json
    - Recarrega agendamentos se 'ultima_modificacao' foi alterado
    - Executa schedule.run_pending()
    - Imprime heartbeat a cada 30s pra sabermos se está vivo
    """
    print("[Scheduler] Iniciando monitor do agendador...")
    registrar_log("scheduler.log", "[Scheduler] monitorar_agendador iniciado.")
    ultima_modificacao_anterior = None
    heartbeat_counter = 0

    while True:
        try:
            config = carregar_horario()
            ultima_modificacao = config.get("ultima_modificacao", "")

            if ultima_modificacao != ultima_modificacao_anterior:
                registrar_log("scheduler.log", 
                    f"[Scheduler] Detecção de alteração em schedule_config.json (ultima_modificacao={ultima_modificacao})."
                )
                atualizar_agendamentos()
                ultima_modificacao_anterior = ultima_modificacao

            schedule.run_pending()

            # Heartbeat a cada 30s, pra ver que não congelou
            heartbeat_counter += 1
            if heartbeat_counter >= 480:
                heartbeat_counter = 0
                registrar_log("scheduler_heartbeat.log", "[Scheduler] still alive...")

            time.sleep(1)

        except Exception as e:
            # Se algo der errado no loop, vamos logar e continuar
            registrar_log("scheduler_fatal.log", 
                f"[Scheduler] ERRO FATAL no loop: {e}\n{traceback.format_exc()}")
            time.sleep(5)  # Evita spam infinito
            # Podemos decidir se continuamos ou damos break:
            # break -> encerraria o scheduler
            # continue -> tenta continuar
            continue

if __name__ == "__main__":
    monitorar_agendador()
