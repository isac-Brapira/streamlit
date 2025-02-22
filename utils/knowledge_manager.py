import streamlit as st
import pandas as pd
import os

from utils.credits import show_credits

# Caminho para o arquivo CSV
CSV_PATH = "knowledge_base.csv"

# Função para carregar o CSV
def load_csv():
    if os.path.exists(CSV_PATH):
        # Lê o CSV com as colunas já definidas na nova estrutura
        df = pd.read_csv(CSV_PATH, delimiter=";", encoding="ISO-8859-1")
        return df
    else:
        return pd.DataFrame(columns=[
            "categoria", "subcategoria", "indicador", "meta", "real", 
            "percentual_atual", "melhores_vendedores", "piores_vendedores", 
            "dias_faltantes", "data_atualizacao", "fonte"
        ])

# Função para salvar o CSV com a nova estrutura
def save_csv(data):
    data.to_csv(CSV_PATH, index=False, sep=";", encoding="ISO-8859-1")

# Função para exportar os dados
def export_data(data, format):
    if format == "CSV":
        return data.to_csv(index=False, sep=";", encoding='ISO-8859-1').encode("ISO-8859-1")
    elif format == "JSON":
        return data.to_json(orient="records", force_ascii=False).encode("utf-8")

def main():
    # Carregar a base de dados
    data = load_csv()

    # Interface Streamlit
    st.title("Configurações")
    st.caption("Adicione, edite ou remova informações da base de dados de forma estruturada.")

    # Campo de busca
    st.subheader("Buscar na Base de Conhecimento")
    search_query = st.text_input("Digite sua busca")
    if search_query:
        # Garantir que as colunas sejam do tipo string
        for col in ["categoria", "subcategoria", "indicador", "fonte"]:
            if col in data.columns:
                data[col] = data[col].astype(str)

        # Aplicar a busca
        filtered_data = data[
            data["categoria"].str.contains(search_query, case=False, na=False) |
            data["subcategoria"].str.contains(search_query, case=False, na=False) |
            data["indicador"].str.contains(search_query, case=False, na=False) |
            data["fonte"].str.contains(search_query, case=False, na=False)
        ]
        st.dataframe(filtered_data)
    else:
        st.dataframe(data)

    # Formulário para adicionar uma nova entrada
    st.subheader("\u2795 Adicionar Nova Informação")
    with st.form("add_entry_form", clear_on_submit=True):
        new_category = st.text_input("Categoria")
        new_subcategory = st.text_input("Subcategoria")
        new_indicator = st.text_area("Indicador")
        new_meta = st.number_input("Meta", min_value=0, step=1)
        new_real = st.number_input("Realizado", min_value=0, step=1)
        new_percentual = st.text_input("Percentual Atingido")
        new_best_sellers = st.text_area("Melhores Vendedores")
        new_worst_sellers = st.text_area("Piores Vendedores")
        new_days_left = st.number_input("Dias Restantes", min_value=0, step=1)
        new_update_date = st.date_input("Data de Atualização")
        new_source = st.text_input("Fonte")
        submitted = st.form_submit_button("Adicionar")
        if submitted:
            if all([new_category, new_subcategory, new_indicator, new_source]):
                new_entry = pd.DataFrame({
                    "categoria": [new_category],
                    "subcategoria": [new_subcategory],
                    "indicador": [new_indicator],
                    "meta": [new_meta],
                    "real": [new_real],
                    "percentual_atual": [new_percentual],
                    "melhores_vendedores": [new_best_sellers],
                    "piores_vendedores": [new_worst_sellers],
                    "dias_faltantes": [new_days_left],
                    "data_atualizacao": [new_update_date],
                    "fonte": [new_source]
                })
                data = pd.concat([data, new_entry], ignore_index=True)
                save_csv(data)
                st.success("Nova entrada adicionada com sucesso!")
            else:
                st.error("Por favor, preencha todos os campos obrigatórios!")

    # Selecionar para editar ou remover uma entrada existente
    st.subheader("\u270F\ufe0f Editar ou Remover Informações")
    if not data.empty:
        if 'indicador' in data.columns:
            selected_index = st.selectbox(
                "Selecione a entrada para editar ou remover", 
                data.index,
                format_func=lambda x: f"{data.iloc[x]['categoria']} - {data.iloc[x]['indicador']}"
            )

            if selected_index is not None:
                category_to_edit = st.text_input("Categoria", data.iloc[selected_index]["categoria"])
                subcategory_to_edit = st.text_input("Subcategoria", data.iloc[selected_index]["subcategoria"])
                indicator_to_edit = st.text_area("Indicador", data.iloc[selected_index]["indicador"])
                meta_to_edit = st.number_input("Meta", value=data.iloc[selected_index]["meta"], min_value=0, step=1)
                real_to_edit = st.number_input("Realizado", value=data.iloc[selected_index]["real"], min_value=0, step=1)
                percentual_to_edit = st.text_input("Percentual Atingido", data.iloc[selected_index]["percentual_atual"])
                best_sellers_to_edit = st.text_area("Melhores Vendedores", data.iloc[selected_index]["melhores_vendedores"])
                worst_sellers_to_edit = st.text_area("Piores Vendedores", data.iloc[selected_index]["piores_vendedores"])
                days_left_to_edit = st.number_input("Dias Restantes", value=data.iloc[selected_index]["dias_faltantes"], min_value=0, step=1)
                update_date_to_edit = st.date_input("Data de Atualização", value=pd.to_datetime(data.iloc[selected_index]["data_atualizacao"]))
                source_to_edit = st.text_input("Fonte", data.iloc[selected_index]["fonte"])

                # Botões para salvar ou excluir
                if st.button("Salvar Alterações"):
                    data.at[selected_index, "categoria"] = category_to_edit
                    data.at[selected_index, "subcategoria"] = subcategory_to_edit
                    data.at[selected_index, "indicador"] = indicator_to_edit
                    data.at[selected_index, "meta"] = meta_to_edit
                    data.at[selected_index, "real"] = real_to_edit
                    data.at[selected_index, "percentual_atual"] = percentual_to_edit
                    data.at[selected_index, "melhores_vendedores"] = best_sellers_to_edit
                    data.at[selected_index, "piores_vendedores"] = worst_sellers_to_edit
                    data.at[selected_index, "dias_faltantes"] = days_left_to_edit
                    data.at[selected_index, "data_atualizacao"] = update_date_to_edit
                    data.at[selected_index, "fonte"] = source_to_edit
                    save_csv(data)
                    st.success("Alterações salvas com sucesso!")

                if st.button("Remover Entrada"):
                    data = data.drop(index=selected_index).reset_index(drop=True)
                    save_csv(data)
                    st.success("Entrada removida com sucesso!")
    else:
        st.info("A base de dados está vazia.")

    show_credits()

if __name__ == "__main__":
    main()
