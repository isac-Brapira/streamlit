import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from fuzzywuzzy import fuzz, process
import os
import json
import re

load_dotenv()

########################################
# 1) LOAD
########################################
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

########################################
# 2) UTILS
########################################
def remove_punct_lower(s: str) -> str:
    """Remove pontuações e converte para minúsculo."""
    s = s.lower()
    s = re.sub(r"[^a-z0-9áàâãéèêíïóôõúç\s]", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def safe_to_float(s: str):
    """Converte string monetária ou numérica para float com segurança."""
    try:
        return float(s.replace('.', '').replace(',', ''))
    except:
        try:
            return float(s)
        except:
            return None

def format_currency(s: str) -> str:
    val = safe_to_float(s)
    if val is not None:
        return f"R$ {val:,.2f}"
    return s

def format_percentage(s: str) -> str:
    """Formata strings como '87%' -> '87%'."""
    s = s.strip()
    if s.endswith('%'):
        try:
            num = float(s[:-1].strip())
            return f"{num:.0f}%"
        except:
            return s
    return s

########################################
# 3) GPT: NOVO TÓPICO
########################################
def analyze_context_with_gpt(user_input, current_context, instructions_df, username="USUARIO"):
    """Analisa se o usuário deseja iniciar um novo tópico."""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, max_tokens=1000)

    system_prompt = f"""
    Você é um assistente que detecta mudança de assunto.
    O usuário se chama {username}. Não confunda o usuário com 'Dados' ou qualquer outra categoria.
    Se o usuário disser algo como 'mudar de assunto', 'trocar de tópico', 'novo tópico', retorne 'novo tópico'.
    Caso contrário, retorne 'continuar'.

    user_input: {user_input}
    current_context: {current_context}
    """

    response = llm.invoke(system_prompt).content.strip().lower()
    if any(kw in response for kw in ["novo tópico","mudar de assunto","trocar de tópico"]):
        return True, "Ok, vamos iniciar um novo tópico."
    return False, "Continuando no mesmo fluxo."

########################################
# 4) handle_detail_level_choice
########################################
def handle_detail_level_choice(choice: str):
    """Identifica se o usuário quer 'detalhado' ou 'resumido' (por exato/fuzzy)."""
    choice_clean = remove_punct_lower(choice)

    # Exato
    if choice_clean in ["detalhado","detalhada","detalhe"]:
        return "Detalhado"
    if choice_clean in ["resumido","resumo"]:
        return "Resumido"

    # Fuzzy
    detail_keywords = ["detalhado","detalhada","detalhe"]
    summary_keywords = ["resumido","resumo"]
    best_score_detail = max(fuzz.partial_ratio(choice_clean,k) for k in detail_keywords)
    best_score_summary = max(fuzz.partial_ratio(choice_clean,k) for k in summary_keywords)

    if best_score_detail >= 70:
        return "Detalhado"
    if best_score_summary >= 70:
        return "Resumido"
    return None

########################################
# 5) MATCH ANY CATEGORY (exceto "dados")
########################################
def match_any_category(question: str, instructions_df: pd.DataFrame) -> str:
    """Faz fuzzy com TODAS as categorias, exceto 'dados'."""
    cats_series = instructions_df["categoria"].dropna().unique()
    cats_list = [c for c in cats_series if c.lower() != "dados"]
    if not cats_list:
        return None

    question_clean = remove_punct_lower(question)
    best, score = process.extractOne(question_clean, cats_list, scorer=fuzz.partial_ratio)
    if best and score>75:
        return best
    return None

########################################
# 6) Função auxiliar: match local com exato + fuzzy
########################################
def match_local_exato_fuzzy(question: str, df_items: pd.DataFrame):
    """
    Recebe DataFrame com colunas: [nome_coluna, sinonimos, descricao, estrategia_resposta].
    Retorna (best_nome, best_desc, best_strat, best_score).
    1) Tenta match exato com nome_coluna e sinonimos => score=100 se bater.
    2) Senão, fuzzy (partial_ratio) => se >=70, retorna.
    """
    def clean_synonyms(syns_str):
        """Garante que os sinônimos sejam strings, mesmo com valores ausentes ou numéricos."""
        if isinstance(syns_str, str):
            return [s.strip() for s in syns_str.split(",") if s.strip()]
        return []  # Retorna lista vazia se não for string

    question_clean = remove_punct_lower(question)
    best_score = 0
    best_nome = None
    best_desc = None
    best_strat = None

    for _, row in df_items.iterrows():
        nome = row.get("nome_coluna", "") or ""
        desc = row.get("descricao", "") or ""
        strat = row.get("estrategia_resposta", "") or ""
        syns_str = row.get("sinonimos", "") or ""

        # Limpeza de sinônimos
        syns = clean_synonyms(syns_str)

        # 1) Check exato
        if remove_punct_lower(nome) == question_clean:
            return nome, desc, strat, 100
        for syn in syns:
            if remove_punct_lower(syn) == question_clean:
                return nome, desc, strat, 100

    # 2) Fuzzy
    for _, row in df_items.iterrows():
        nome = row.get("nome_coluna", "") or ""
        desc = row.get("descricao", "") or ""
        strat = row.get("estrategia_resposta", "") or ""
        syns_str = row.get("sinonimos", "") or ""

        # Limpeza de sinônimos
        syns = clean_synonyms(syns_str)

        # Monta doc para fuzzy
        doc_pieces = [str(piece) for piece in [nome] + syns + [desc, strat]]
        doc_clean = remove_punct_lower(" ".join(doc_pieces))

        sc = fuzz.partial_ratio(question_clean, doc_clean)
        if sc > best_score:
            best_score = sc
            best_nome = nome
            best_desc = desc
            best_strat = strat

    if best_score >= 70:
        return best_nome, best_desc, best_strat, best_score
    return None, None, None, 0


########################################
# 7) match_dados_local com exato + fuzzy
########################################
def match_dados_local(question: str, instructions_df: pd.DataFrame):
    df_dados = instructions_df[instructions_df["categoria"].str.lower()=="dados"]
    if df_dados.empty:
        return None, None, None, 0

    nome, desc, strat, score = match_local_exato_fuzzy(question, df_dados)
    return nome, desc, strat, score

########################################
# 8) fallback_gpt_data (sem mudança, mas iremos checar exato antes do fallback)
########################################
def fallback_gpt_data(question: str, instructions_df: pd.DataFrame, username="USUARIO"):
    df_dados = instructions_df[instructions_df["categoria"].str.lower()=="dados"]
    if df_dados.empty:
        return None, None, None

    knowledge_list = []
    for _, row in df_dados.iterrows():
        nome = row.get("nome_coluna","")
        desc = row.get("descricao","")
        strat = row.get("estrategia_resposta","")
        syns = row.get("sinonimos","") or ""
        knowledge_list.append({
            "nome_coluna": nome,
            "descricao": desc,
            "estrategia_resposta": strat,
            "sinonimos": syns
        })

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, max_tokens=1000)
    system_prompt = f"""
    Você é um assistente que recebe uma lista de 'Dados'.
    O usuário se chama {username}. Não confunda o usuário com 'Dados'.
    Tente adivinhar se o input se refere a alguma dessas linhas,
    ou retorne {{'nome_coluna': null, 'descricao': null, 'estrategia_resposta': null}} se não conseguir.
    """
    user_prompt = f"User input: {question}\nLista de Dados:\n{knowledge_list}\n"

    msgs = [
        {"role":"system","content":system_prompt},
        {"role":"user","content":user_prompt}
    ]
    raw = llm.invoke(msgs).content.strip()
    try:
        data = json.loads(raw)
        nm = data.get("nome_coluna")
        ds = data.get("descricao")
        stt = data.get("estrategia_resposta")
        if nm is None or ds is None or stt is None:
            return None,None,None
        return nm, ds, stt
    except:
        return None,None,None

########################################
# 9) match_any_item_in_category com exato + fuzzy
########################################
def match_any_item_in_category(category: str, question: str, instructions_df: pd.DataFrame):
    df_cat = instructions_df[instructions_df["categoria"].str.lower()==category.lower()]
    if df_cat.empty:
        return None, None, None, 0

    nome, desc, strat, score = match_local_exato_fuzzy(question, df_cat)
    return nome, desc, strat, score

########################################
# 10) fallback_gpt_generic_category
########################################
def fallback_gpt_generic_category(category: str, question: str, instructions_df: pd.DataFrame, username="USUARIO"):
    df_cat = instructions_df[instructions_df["categoria"].str.lower() == category.lower()]
    if df_cat.empty:
        return None, None, None, 0  # Certifique-se de que retorna 4 valores

    knowledge_list = []
    for _, row in df_cat.iterrows():
        nm = row.get("nome_coluna", "")
        ds = row.get("descricao", "")
        stt = row.get("estrategia_resposta", "")
        syns = row.get("sinonimos", "") or ""
        knowledge_list.append({
            "nome_coluna": nm,
            "descricao": ds,
            "estrategia_resposta": stt,
            "sinonimos": syns
        })

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, max_tokens=1000)
    system_prompt = f"""Você é um assistente que recebe uma lista de itens da categoria '{category}'.
        O usuário se chama {username}. Não confunda o usuário com 'Dados'.
        Tente adivinhar se ele se refere a alguma dessas linhas,
        ou retorne {{ "nome_coluna": null, "descricao": null, "estrategia_resposta": null }} se não conseguir.
        """
    user_prompt = f"User input: {question}\nLista de itens da categoria '{category}':\n{knowledge_list}\n"

    msgs = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    raw = llm.invoke(msgs).content.strip()
    try:
        data = json.loads(raw)
        nm = data.get("nome_coluna")
        ds = data.get("descricao")
        stt = data.get("estrategia_resposta")
        if nm is None or ds is None or stt is None:
            return None, None, None, 0  # Certifique-se de que retorna 4 valores
        return nm, ds, stt, 1  # Adiciona um score fixo de 1 (ou calcule conforme necessário)
    except:
        return None, None, None, 0  # Retorno padrão


########################################
# 11) generate_generic_response
########################################
def generate_generic_response(nome: str, desc: str, strat: str, username="USUARIO") -> str:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.9, max_tokens=1000)

    system_prompt = f"""
    Você é um assistente criativo.
    O usuário se chama {username}.
    """

    user_prompt = f"""
    O usuário busca informação sobre '{nome}'.
    Descrição: '{desc}'.
    Estratégia (não revelar!): '{strat}'.

    Crie uma resposta que:
    - Utilize a descrição para informar.
    - Aplique a estratégia (se for 'engraçada', faça piadas).
    - NÃO exiba o texto da estratégia diretamente.
    - Seja criativa e clara.
    """

    msgs = [
        {"role":"system","content":system_prompt},
        {"role":"user","content":user_prompt}
    ]
    response = llm.invoke(msgs).content.strip()
    return response

########################################
# 12) generate_final_response (KPI/Recurso)
########################################
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

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, max_tokens=1000)

    if detail=="Detalhado":
        st.session_state.detail_level = None
        system_prompt = f"""
        Você é um analista comercial conciso e objetivo.
        O usuário se chama {username}.
        """

        user_prompt = f"""
        - Indicador/Recurso: {indicator_name}
        - Categoria: {cat}

        Descrição: "{desc}"
        Estratégia: "{strategy}"

        # Dados do knowledge_base:
        Meta: {meta}
        Real: {real}
        Percentual: {perc}
        Melhores Vendedores: {best_sellers}
        Piores Vendedores: {worst_sellers}
        Dias Restantes: {dias_falt}
        Última Atualização: {data_upd}

        Não reexplique o que é o indicador ou recurso.
        Foque em insights e ações de melhoria.
        Seja icônica no retorno.
        """

        msgs = [
            {"role":"system","content":system_prompt},
            {"role":"user","content":user_prompt}
        ]
        return llm.invoke(msgs).content.strip()
    else:
        # Resumido
        st.session_state.detail_level = None
        if cat.lower()=="kpi":
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
                text+=f"- Faltam {format_currency(str(faltam))} para a meta, com {dias_falt} dias restantes.\n"
            else:
                text+=f"- Dias Restantes: {dias_falt}\n"
            text+=f"- Última Atualização: {data_upd}"
            return text.strip()
        else:
            text = f"""
                **{indicator_name}** (Recurso)

                - Recurso Disponível: {format_currency(meta)}
                - Recurso Utilizado: {format_currency(real)}
                - Percentual Utilizado: {format_percentage(perc)}
                - Última atualização: {data_upd}
                """
            return text.strip()

########################################
# 13) generate_response
########################################
def generate_response(user_input: str, knowledge_base: pd.DataFrame, instructions_df: pd.DataFrame):
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

    # 1) Verifica se é "novo tópico"
    is_new_topic, gpt_feedback = analyze_context_with_gpt(user_input, current_context, instructions_df, username=username)
    st.write(f"**[Insight do Sônico]:** {gpt_feedback}")

    # 2) Se for novo tópico, limpa states
    if is_new_topic:
        st.session_state.current_category = None
        st.session_state.current_kpi = None
        st.session_state.detail_level = None

    user_input_lower = remove_punct_lower(user_input)

    # 3) "voltar"/"menu"
    if user_input_lower in ["voltar","menu"]:
        st.session_state.current_kpi = None
        st.session_state.detail_level = None
        return "OK, vamos escolher outra categoria."

    # 4) Se já temos cat+kpi mas não detail, e user diz "detalhado"/"resumido"
    detail_choice = handle_detail_level_choice(user_input_lower)
    if detail_choice and st.session_state.current_category and st.session_state.current_kpi:
        st.session_state.detail_level = detail_choice
        return generate_final_response(knowledge_base, instructions_df)

    # 5) Verifica se o user_input corresponde a alguma categoria (exceto 'dados')
    cat_guess = match_any_category(user_input_lower, instructions_df)
    if cat_guess and cat_guess.lower() != (st.session_state.current_category or "").lower():
        st.session_state.current_category = cat_guess
        st.session_state.current_kpi = None
        st.session_state.detail_level = None

        if cat_guess.lower() in ["kpi","recurso"]:
            cat_rows = instructions_df[instructions_df["categoria"].str.lower()==cat_guess.lower()]
            if not cat_rows.empty:
                st.caption(cat_rows.iloc[0].get("descricao_categoria",""))
                cat_opts = cat_rows["nome_coluna"].unique()
                return f"As opções em {cat_guess} são: {', '.join(cat_opts)}. Poderia especificar?"
            else:
                return f"OK, categoria={cat_guess}, mas não achei indicadores."
        else:
            # Categoria genérica
            df_catdesc = instructions_df[
                (instructions_df["categoria"].str.lower()==cat_guess.lower()) &
                (instructions_df["descricao_categoria"].notna())
            ]
            if not df_catdesc.empty:
                st.caption(df_catdesc.iloc[0]["descricao_categoria"])

            cat_items = instructions_df[
                instructions_df["categoria"].str.lower()==cat_guess.lower()
            ]["nome_coluna"].unique()
            if len(cat_items)>0:
                return f"As opções em {cat_guess} são: {', '.join(cat_items)}. Poderia especificar?"
            else:
                return f"Categoria '{cat_guess}' identificada, mas sem itens mapeados. O que deseja saber?"

    # 6) Tenta "dados" local (exato + fuzzy)
    dados_nome, dados_desc, dados_strat, dados_score = match_dados_local(user_input_lower, instructions_df)
    if dados_score>=70:  # Abaixamos para 70 se quiser ser mais permissivo
        return generate_generic_response(dados_nome, dados_desc, dados_strat, username=username)

    # 6.1) fallback GPT p/ "dados"
    fb_nm, fb_desc, fb_strat = fallback_gpt_data(user_input, instructions_df, username=username)
    if fb_nm and fb_desc and fb_strat:
        return generate_generic_response(fb_nm, fb_desc, fb_strat, username=username)

    # 7) Se a current_category for kpi/recurso, tenta match local p/ kpi
    if st.session_state.current_category and st.session_state.current_category.lower() in ["kpi","recurso"]:
        from textwrap import dedent
        local_cat, local_name, local_score = match_kpi_recurso_local(user_input_lower, instructions_df)
        if local_score>=70:
            st.session_state.current_category = local_cat
            st.session_state.current_kpi = local_name
            st.session_state.detail_level = None
            return "Você gostaria de um nível de detalhe 'detalhado' ou 'resumido'?"

        # fallback GPT p/ KPI/Recurso
        cat_gpt, nm_gpt, fb_desc, fb_score = fallback_gpt_generic_category(st.session_state.current_category, user_input, instructions_df, username=username)

        if cat_gpt and nm_gpt:
            st.session_state.current_category = cat_gpt
            st.session_state.current_kpi = nm_gpt
            st.session_state.detail_level = None
            return "Você gostaria de um nível de detalhe 'detalhado' ou 'resumido'?"

    # 8) Se a current_category for genérica (ex.: "eventos")
    if st.session_state.current_category and st.session_state.current_category.lower() not in ["kpi","recurso","dados"]:
        gen_nm, gen_desc, gen_strat, gen_score = match_any_item_in_category(
            st.session_state.current_category, user_input_lower, instructions_df
        )
        if gen_score>=70:
            return generate_generic_response(gen_nm, gen_desc, gen_strat, username=username)

        fb_gen_nm, fb_gen_desc, fb_gen_strat = fallback_gpt_generic_category(
            st.session_state.current_category, user_input, instructions_df, username=username
        )
        if fb_gen_nm and fb_gen_desc and fb_gen_strat:
            return generate_generic_response(fb_gen_nm, fb_gen_desc, fb_gen_strat, username=username)

    # 9) Se nada encontrado => listamos as categorias (exceto 'dados')
    all_cats = instructions_df["categoria"].dropna().unique()
    visible_cats = [c for c in all_cats if c.lower()!="dados"]
    if visible_cats:
        cats_str = ", ".join(set(visible_cats))
        return f"Não entendi sua solicitação. Categorias disponíveis: {cats_str}."
    else:
        return "Não entendi sua solicitação, e não há categorias cadastradas."


########################################
# 14) match_kpi_recurso_local com exato + fuzzy
########################################
def match_kpi_recurso_local(question: str, instructions_df: pd.DataFrame):
    """Semelhante ao 'dados', mas para categorias ['kpi', 'recurso'].""" 
    relevant_df = instructions_df[
        instructions_df["categoria"].str.lower().isin(["kpi", "recurso"])
    ]
    if relevant_df.empty:
        return None, None, 0

    def clean_synonyms(syns_str):
        """Garante que os sinônimos sejam strings, mesmo com valores ausentes ou numéricos."""
        if isinstance(syns_str, str):
            return [s.strip() for s in syns_str.split(",") if s.strip()]
        return []  # Retorna lista vazia se não for string

    # Processamento de fuzzy/exato
    question_clean = remove_punct_lower(question)
    best_score = 0
    best_category = None
    best_name = None

    for _, row in relevant_df.iterrows():
        cat = row.get("categoria", "")
        nome = row.get("nome_coluna", "") or ""
        desc = row.get("descricao", "") or ""
        strat = row.get("estrategia_resposta", "") or ""
        syns_str = row.get("sinonimos", "") or ""

        # Limpeza de sinônimos
        syns = clean_synonyms(syns_str)

        # Monta doc para fuzzy
        doc_pieces = [str(piece) for piece in [nome] + syns + [desc, strat]]
        doc_clean = remove_punct_lower(" ".join(doc_pieces))

        sc = fuzz.partial_ratio(question_clean, doc_clean)
        if sc > best_score:
            best_score = sc
            best_category = cat
            best_name = nome

    if best_score >= 70:
        return best_category, best_name, best_score
    return None, None, 0


########################################
# 15) MAIN
########################################
def main():
    st.title("Atendente Comercial")

    # Definimos username manualmente (exemplo). Em um app real, usar login.
    if "username" not in st.session_state:
        st.session_state.username = "Admin"

    instructions_df = load_instructions()
    knowledge_base_df = load_csv()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Exibe histórico anterior
    for msg in st.session_state.messages:
        if msg["role"]=="user":
            st.chat_message("user").write(msg["content"])
        else:
            st.chat_message("assistant").write(msg["content"])

    user_input = st.chat_input("Digite sua pergunta aqui...")
    if user_input:
        st.session_state.messages.append({"role":"user","content":user_input})
        st.chat_message("user").write(user_input)

        response = generate_response(user_input, knowledge_base_df, instructions_df)

        st.session_state.messages.append({"role":"assistant","content":response})
        st.chat_message("assistant").markdown(response)

if __name__=="__main__":
    main()
