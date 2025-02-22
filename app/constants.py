# app/constants.py
import os

CONFIG_FILE = "rotinas_config.json"
SCHEDULE_FILE = "schedule_config.json"
SCHEDULER_SCRIPT = "scheduler_intermediador.py"
PIDFILE_NAME = "scheduler_pid.txt"

# Diretório de logs (use local ou em rede, a seu critério)
LOG_DIRECTORY = r"\\192.168.1.213\Arquivos\Administrativo\TecInfo\DESENVOLVIMENTOS\atendente-IA-v1\Logs"

INTERVALO_MINIMO = 30

# Rotinas disponíveis
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
    ("Tabelas Escalonadas", "01250802"),
]