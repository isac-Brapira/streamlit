import streamlit as st
import pandas as pd
import os
import re

@st.cache_data(ttl=60)
def load_csv(file_path="knowledge_base.csv"):
    if os.path.exists(file_path):
        return pd.read_csv(file_path, delimiter=";", encoding="ISO-8859-1")
    else:
        return pd.DataFrame(
            columns=[
                "categoria","subcategoria","indicador","meta","real","percentual_atual",
                "melhores_vendedores","piores_vendedores","dias_faltantes","data_atualizacao","fonte"
            ]
        )

@st.cache_data(ttl=60)
def load_instructions(file_path="instructions.csv"):
    if os.path.exists(file_path):
        return pd.read_csv(file_path, delimiter=";", encoding="ISO-8859-1")
    else:
        return pd.DataFrame(
            columns=[
                "categoria","descricao_categoria","nome_coluna","descricao","sinonimos","estrategia_resposta"
            ]
        )
