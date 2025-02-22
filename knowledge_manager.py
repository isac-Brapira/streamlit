# knowledge_manager.py

import streamlit as st
import pandas as pd
import os
from utils.credits import show_credits

CSV_PATH = "knowledge_base.csv"

def load_csv():
    if os.path.exists(CSV_PATH):
        df = pd.read_csv(CSV_PATH, delimiter=";", encoding="ISO-8859-1")
        return df
    else:
        return pd.DataFrame(columns=[
            "categoria","subcategoria","indicador","meta","real",
            "percentual_atual","melhores_vendedores","piores_vendedores",
            "dias_faltantes","data_atualizacao","fonte"
        ])

def save_csv(data):
    data.to_csv(CSV_PATH, index=False, sep=";", encoding="ISO-8859-1")

def export_data(data, format):
    if format == "CSV":
        return data.to_csv(index=False, sep=";", encoding='ISO-8859-1').encode("ISO-8859-1")
    elif format == "JSON":
        return data.to_json(orient="records", force_ascii=False).encode("utf-8")

def main():
    data = load_csv()

    # Converte a coluna 'real' (se existir) para numérico, evitando erro em st.number_input
    if "real" in data.columns:
        data["real"] = pd.to_numeric(data["real"], errors="coerce").fillna(0)

    st.title("Configurações")
    st.caption("Adicione, edite ou remova informações da base de dados de forma estruturada.")

    # Exemplo de uso normal do DataFrame:
    # ...
    # Aqui no form de edição, ao usar st.number_input, converta para int/float

    # Exibir tabela ou filtrar
    st.subheader("Buscar na Base de Conhecimento")
    search_query = st.text_input("Digite sua busca")
    if search_query:
        for col in ["categoria", "subcategoria", "indicador", "fonte"]:
            if col in data.columns:
                data[col] = data[col].astype(str)
        filtered_data = data[
            data["categoria"].str.contains(search_query, case=False, na=False)
            | data["subcategoria"].str.contains(search_query, case=False, na=False)
            | data["indicador"].str.contains(search_query, case=False, na=False)
            | data["fonte"].str.contains(search_query, case=False, na=False)
        ]
        st.dataframe(filtered_data)
    else:
        st.dataframe(data)

    # Exemplo: Formulário para adicionar
    st.subheader("\u2795 Adicionar Nova Informação")
    with st.form("add_entry_form", clear_on_submit=True):
        new_category = st.text_input("Categoria")
        new_subcategory = st.text_input("Subcategoria")
        new_indicator = st.text_area("Indicador")
        new_meta = st.number_input("Meta", min_value=0, step=1)
        new_real = st.number_input("Realizado", min_value=0, step=1)
        # ...
        submitted = st.form_submit_button("Adicionar")
        if submitted:
            # salva no DF e no CSV ...
            pass

    # Exemplo: Edição/Remoção
    st.subheader("\u270F\ufe0f Editar ou Remover Informações")
    if not data.empty and "indicador" in data.columns:
        selected_index = st.selectbox(
            "Selecione a entrada para editar ou remover",
            data.index,
            format_func=lambda x: f"{data.iloc[x]['categoria']} - {data.iloc[x]['indicador']}"
        )
        if selected_index is not None:
            # Exemplo de pegar valor numérico
            meta_val = int(data.at[selected_index, "meta"]) if not pd.isnull(data.at[selected_index, "meta"]) else 0
            meta_to_edit = st.number_input("Meta", value=meta_val, min_value=0, step=1)

            real_val = float(data.at[selected_index, "real"]) if not pd.isnull(data.at[selected_index, "real"]) else 0.0
            real_to_edit = st.number_input("Realizado", value=real_val, min_value=0.0, step=1.0)

            # ...
            if st.button("Salvar Alterações"):
                data.at[selected_index, "meta"] = meta_to_edit
                data.at[selected_index, "real"] = real_to_edit
                # ...
                save_csv(data)
                st.success("Alterações salvas com sucesso!")

            if st.button("Remover Entrada"):
                data = data.drop(index=selected_index).reset_index(drop=True)
                save_csv(data)
                st.success("Entrada removida com sucesso!")
    else:
        st.info("A base de dados está vazia ou sem coluna 'indicador'.")

    show_credits()
