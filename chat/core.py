import streamlit as st
import pandas as pd

from .utils import safe_to_float, format_currency, format_percentage
from .gpt import (
    analyze_context_with_gpt,
    fallback_gpt_data,
    fallback_gpt_generic_category,
    generate_generic_response
)
from .matchers import (
    handle_detail_level_choice,
    match_any_category,
    match_dados_local,
    match_any_item_in_category,
    match_kpi_recurso_local
)

MONTH_NAMES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
]

def _format_int_thousands(num: float) -> str:
    """
    Converte o float para int (arredondando) e formata com '.' como separador de milhar.
    Exemplo: 34040016.7399999 => 34.040.017
    """
    val_int = int(round(num))  # Arredonda antes de converter para int
    return f"{val_int:,}".replace(",", ".")

def _parse_faturamento_ano(real_str: str) -> list:
    """
    Recebe a string com valores em pares (ex: "34040016,7399999,31044659,8699998,...").
    Cada par corresponde a 1 mês: ex.: "34040016" e "7399999" => float(34040016.7399999).
    Em seguida arredondamos para int e formatamos no estilo "34.040.016".

    Retorna uma lista [(mes, valor_formatado), ...] com no máximo 12 meses.
    """
    parts = [p.strip() for p in real_str.split(",")]
    paired_vals = []

    for i in range(0, len(parts), 2):
        if (i + 1) < len(parts):
            # Há um "par" (parte_int + parte_dec)
            parte_int = parts[i].replace(",", ".")   # ex: "34040016"
            parte_dec = parts[i+1].replace(",", ".") # ex: "7399999"
            try:
                val = float(f"{parte_int}.{parte_dec}")  # 34040016.7399999
            except ValueError:
                val = 0.0
            paired_vals.append(val)
        else:
            # Se sobrou só a parte_int
            try:
                val = float(parts[i].replace(",", "."))
            except ValueError:
                val = 0.0
            paired_vals.append(val)

    # Montar lista final com até 12 meses
    results = []
    max_months = min(len(paired_vals), 12)
    for idx in range(max_months):
        mes = MONTH_NAMES[idx]
        val_str_formatted = _format_int_thousands(paired_vals[idx])
        results.append((mes, val_str_formatted))
    return results

def _build_faturamento_table_generic(real_str: str, titulo="Faturamento") -> str:
    """
    Para Faturamento 2024 ou 2025: gera uma tabela com (Mês, Faturamento (R$)),
    respeitando no máximo 12 pares de valores.
    """
    valores = _parse_faturamento_ano(real_str)
    txt = f"{titulo}:\nMês\tFaturamento (R$)\n"
    for (mes, val) in valores:
        txt += f"{mes}\t{val}\n"
    return txt

def _build_faturamento_table_2024_2025(real_str: str) -> str:
    """
    Para 'Faturamento 2024 x 2025', a string vem no formato:
      "12589907,71,0,0,... / 34040016,7399999,31044659,8699998,..."
    Construímos duas tabelas: primeira (2025) e depois (2024), cada uma com até 12 valores.
    """
    sides = [x.strip() for x in real_str.split("/")]
    if len(sides) != 2:
        # Se não estiver no formato esperado, gera uma só
        return _build_faturamento_table_generic(real_str, "Faturamento Desconhecido")

    # Lado 1: 2025
    tabela_2025 = _parse_faturamento_ano(sides[0])
    txt_2025 = "Faturamento 2025:\nMês\tFaturamento (R$)\n"
    for (mes, val) in tabela_2025:
        txt_2025 += f"{mes}\t{val}\n"

    # Lado 2: 2024
    tabela_2024 = _parse_faturamento_ano(sides[1])
    txt_2024 = "\nFaturamento 2024:\nMês\tFaturamento (R$)\n"
    for (mes, val) in tabela_2024:
        txt_2024 += f"{mes}\t{val}\n"

    return txt_2025 + "\n" + txt_2024

def generate_final_response(knowledge_base: pd.DataFrame, instructions_df: pd.DataFrame):
    cat = st.session_state.current_category
    kpi = st.session_state.current_kpi
    detail = st.session_state.detail_level
    username = st.session_state.get("username","USUARIO")

    df = knowledge_base[
        (knowledge_base["categoria"].str.lower()==cat.lower()) &
        (knowledge_base["indicador"].str.lower()==kpi.lower())
    ]
    if df.empty:
        st.session_state.detail_level = None
        return "Não encontrei dados para esse indicador/recurso na base."

    row = df.iloc[0]
    instr_df = instructions_df[
        (instructions_df["categoria"].str.lower()==cat.lower()) &
        (instructions_df["nome_coluna"].str.lower()==kpi.lower())
    ]
    if instr_df.empty:
        instr_df = instructions_df[instructions_df["categoria"].str.lower()==cat.lower()]
    irow = instr_df.iloc[0]

    meta = row.get("meta","")
    real = row.get("real","")
    perc = row.get("percentual_atual","")
    best_sellers = row.get("melhores_vendedores","")
    worst_sellers = row.get("piores_vendedores","")
    dias_falt = row.get("dias_faltantes","")
    data_upd = row.get("data_atualizacao","")
    indicator_name = row.get("indicador","")

    desc = irow.get("descricao","")
    strategy = irow.get("estrategia_resposta","")

    is_fat_2024 = (indicator_name.lower() == "faturamento 2024")
    is_fat_2025 = (indicator_name.lower() == "faturamento 2025")
    is_fat_24x25 = ("2024 x 2025" in indicator_name.lower())

    if detail == "Detalhado":
        st.session_state.detail_level = None
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, max_tokens=1000)

        # Se Faturamento 2024, 2025 ou 2024 x 2025, gera tabela customizada
        if (is_fat_2024 or is_fat_2025 or is_fat_24x25) and isinstance(real, str):
            if is_fat_24x25:
                tabelas = _build_faturamento_table_2024_2025(real)
            else:
                ano = indicator_name[-4:].strip()  # ex.: "2024"
                tabelas = _build_faturamento_table_generic(real, f"Faturamento {ano}")
            extra_table_info = tabelas
        else:
            extra_table_info = ""

        system_prompt = f"""
        Você é um analista comercial conciso. O usuário se chama {username}.
        Se for Faturamento (2024, 2025 ou 2024 x 2025), inclua a tabela no retorno,
        sem alterar os valores. Depois, ofereça insights de melhoria.
        """

        user_prompt = f"""
        Indicador/Recurso: {indicator_name}
        Categoria: {cat}

        Descrição no instructions.csv: "{desc}"
        Estratégia: "{strategy}"

        # Dados do knowledge_base:
        Meta: {meta}
        Real (bruta): {real}
        Percentual: {perc}
        Melhores Vendedores: {best_sellers}
        Piores Vendedores: {worst_sellers}
        Dias Restantes: {dias_falt}
        Última Atualização: {data_upd}

        ----------Tabela----------
        {extra_table_info}
        --------------------------

        Regras:
        - Se for Faturamento, retorne a informação em formato de tabela. Crie uma lista com quebras de linhas com os melhores e os piores vendedores.
        - Não reexplique demais o indicador; dê insights de melhoria (vendedores, melhores práticas, etc.).
        - Se for retornar informações sobre o faturamento (Provavelmente será em R$), garanta que a saída não contenha as casas decimais dos centavos e esteja formatada.
        - Garanta a aplicação da {strategy} no retorno, mas não revele-a ao usuário.
        """

        msgs = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        return llm.invoke(msgs).content.strip()

    else:
        # Modo Resumido
        st.session_state.detail_level = None
        if cat.lower() == "kpi":
            val_meta = safe_to_float(meta)
            val_real = safe_to_float(real)
            faltam = None
            if val_meta is not None and val_real is not None:
                faltam = val_meta - val_real

            text = f"""
            **{indicator_name}** (KPI)

            - Meta: {format_currency(meta)}
            - Real: {format_currency(real)}
            - Percentual: {format_percentage(perc)}
            - Melhores Vendedores: {best_sellers}
            - Piores Vendedores: {worst_sellers}
            """
            if faltam is not None:
                text += f"- Faltam {format_currency(str(faltam))} para a meta, com {dias_falt} dias restantes.\n"
            else:
                text += f"- Dias Restantes: {dias_falt}\n"
            text += f"- Última Atualização: {data_upd}"

            return text.strip()
        else:
            # Recurso
            text = f"""
            **{indicator_name}** (Recurso)

            - Recurso Disponível: {format_currency(meta)}
            - Recurso Utilizado: {format_currency(real)}
            - Percentual Utilizado: {format_percentage(perc)}
            - Última atualização: {data_upd}
            """
            return text.strip()

def generate_response(user_input: str, knowledge_base: pd.DataFrame, instructions_df: pd.DataFrame):
    """
    Fluxo principal. No modo Detalhado, agora exibimos a tabela
    com valores full int formatados em grupos de mil, ex.: '34.040.016'.
    """
    if "current_category" not in st.session_state:
        st.session_state.current_category = None
    if "current_kpi" not in st.session_state:
        st.session_state.current_kpi = None
    if "detail_level" not in st.session_state:
        st.session_state.detail_level = None
    if "username" not in st.session_state:
        st.session_state.username = "USUARIO"

    username = st.session_state.username
    current_context = {
        "current_category": st.session_state.current_category,
        "current_kpi": st.session_state.current_kpi,
        "detail_level": st.session_state.detail_level,
        "username": username
    }

    # Detectar "novo tópico"
    is_new_topic, gpt_feedback = analyze_context_with_gpt(
        user_input, current_context, instructions_df, username=username
    )
    st.write(f"**[Insight do Sônico]:** {gpt_feedback}")

    if is_new_topic:
        st.session_state.current_category = None
        st.session_state.current_kpi = None
        st.session_state.detail_level = None

    user_input_lower = user_input.lower().strip()

    # Comandos "voltar"/"menu"
    if user_input_lower in ["voltar","menu"]:
        st.session_state.current_kpi = None
        st.session_state.detail_level = None
        return "OK, vamos escolher outra categoria."

    # Se já temos cat+kpi mas sem detail e user pede "detalhado"/"resumido"
    detail_choice = handle_detail_level_choice(user_input_lower)
    if detail_choice and st.session_state.current_category and st.session_state.current_kpi:
        st.session_state.detail_level = detail_choice
        return generate_final_response(knowledge_base, instructions_df)

    # Se ainda não temos category, tenta match_kpi_recurso_local
    if st.session_state.current_category is None:
        local_cat, local_name, local_score = match_kpi_recurso_local(user_input_lower, instructions_df)
        if local_score >= 70 and local_cat and local_name:
            st.session_state.current_category = local_cat
            st.session_state.current_kpi = local_name
            st.session_state.detail_level = None
            return "Você gostaria de um nível de detalhe 'detalhado' ou 'resumido'?"

    # Tenta reconhecer se user escolheu nova categoria
    cat_guess = match_any_category(user_input_lower, instructions_df)
    if cat_guess and cat_guess.lower() != (st.session_state.current_category or "").lower():
        st.session_state.current_category = cat_guess
        st.session_state.current_kpi = None
        st.session_state.detail_level = None

        cat_rows = instructions_df[instructions_df["categoria"].str.lower()==cat_guess.lower()]
        if not cat_rows.empty:
            st.caption(cat_rows.iloc[0].get("descricao_categoria",""))
            cat_opts = cat_rows["nome_coluna"].unique()
            lines = "\n".join([f"- {opt}" for opt in cat_opts])
            return f"As opções em {cat_guess} são:\n{lines}\nPoderia especificar?"
        else:
            return f"OK, categoria={cat_guess}, mas não achei indicadores."

    # Tenta "dados" local
    dados_nome, dados_desc, dados_strat, dados_score = match_dados_local(user_input_lower, instructions_df)
    if dados_score >= 70:
        return generate_generic_response(dados_nome, dados_desc, dados_strat, username=username)

    # fallback GPT p/ "dados"
    fb_nm, fb_desc, fb_strat = fallback_gpt_data(user_input, instructions_df, username=username)
    if fb_nm and fb_desc and fb_strat:
        return generate_generic_response(fb_nm, fb_desc, fb_strat, username=username)

    # Se a current_category for kpi/recurso e user especifica item
    if (st.session_state.current_category
        and st.session_state.current_category.lower() in ["kpi","recurso"]):
        local_cat, local_name, local_score = match_kpi_recurso_local(user_input_lower, instructions_df)
        if local_score >= 70:
            st.session_state.current_category = local_cat
            st.session_state.current_kpi = local_name
            st.session_state.detail_level = None
            return "Você gostaria de um nível de detalhe 'detalhado' ou 'resumido'?"

        # fallback GPT p/ KPI/Recurso
        cat_gpt, nm_gpt, fb_desc, fb_score = fallback_gpt_generic_category(
            st.session_state.current_category,
            user_input,
            instructions_df,
            username=username
        )
        if cat_gpt and nm_gpt:
            st.session_state.current_category = cat_gpt
            st.session_state.current_kpi = nm_gpt
            st.session_state.detail_level = None
            return "Você gostaria de um nível de detalhe 'detalhado' ou 'resumido'?"

    # Se a current_category for genérica
    if (st.session_state.current_category
        and st.session_state.current_category.lower() not in ["kpi","recurso","dados"]):
        gen_nm, gen_desc, gen_strat, gen_score = match_any_item_in_category(
            st.session_state.current_category,
            user_input_lower,
            instructions_df
        )
        if gen_score>=70:
            return generate_generic_response(gen_nm, gen_desc, gen_strat, username=username)

        fb_gen_nm, fb_gen_desc, fb_gen_strat, _ = fallback_gpt_generic_category(
            st.session_state.current_category,
            user_input,
            instructions_df,
            username=username
        )
        if fb_gen_nm and fb_gen_desc and fb_gen_strat:
            return generate_generic_response(fb_gen_nm, fb_gen_desc, fb_gen_strat, username=username)

    # Nada encontrado => listar categorias
    all_cats = instructions_df["categoria"].dropna().unique()
    visible_cats = [c for c in all_cats if c.lower()!="dados"]
    if visible_cats:
        cats_str = "\n".join([f"- {x}" for x in sorted(set(visible_cats))])
        return f"Não entendi sua solicitação.\nCategorias disponíveis:\n{cats_str}"
    else:
        return "Não entendi sua solicitação, e não há categorias cadastradas."
