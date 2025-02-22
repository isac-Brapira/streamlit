from fuzzywuzzy import fuzz, process
import pandas as pd
from .utils import remove_punct_lower

def handle_detail_level_choice(choice: str):
    """Identifica se o usuário quer 'detalhado' ou 'resumido'."""
    choice_clean = remove_punct_lower(choice)

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

def match_local_exato_fuzzy(question: str, df_items: pd.DataFrame):
    """
    Recebe DataFrame com colunas: [nome_coluna, sinonimos, descricao, estrategia_resposta].
    Faz match exato e fuzzy. Retorna (best_nome, best_desc, best_strat, best_score).
    """
    def clean_synonyms(syns_str):
        if isinstance(syns_str, str):
            return [s.strip() for s in syns_str.split(",") if s.strip()]
        return []

    question_clean = remove_punct_lower(question)
    best_score = 0
    best_nome = None
    best_desc = None
    best_strat = None

    # 1) match exato
    for _, row in df_items.iterrows():
        nome = row.get("nome_coluna", "") or ""
        desc = row.get("descricao", "") or ""
        strat = row.get("estrategia_resposta", "") or ""
        syns_str = row.get("sinonimos", "") or ""
        syns = clean_synonyms(syns_str)

        if remove_punct_lower(nome) == question_clean:
            return nome, desc, strat, 100
        for syn in syns:
            if remove_punct_lower(syn) == question_clean:
                return nome, desc, strat, 100

    # 2) fuzzy
    for _, row in df_items.iterrows():
        nome = row.get("nome_coluna", "") or ""
        desc = row.get("descricao", "") or ""
        strat = row.get("estrategia_resposta", "") or ""
        syns_str = row.get("sinonimos", "") or ""
        syns = clean_synonyms(syns_str)

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

def match_dados_local(question: str, instructions_df: pd.DataFrame):
    df_dados = instructions_df[instructions_df["categoria"].str.lower()=="dados"]
    if df_dados.empty:
        return None, None, None, 0

    nome, desc, strat, score = match_local_exato_fuzzy(question, df_dados)
    return nome, desc, strat, score

def match_any_item_in_category(category: str, question: str, instructions_df: pd.DataFrame):
    df_cat = instructions_df[instructions_df["categoria"].str.lower()==category.lower()]
    if df_cat.empty:
        return None, None, None, 0

    nome, desc, strat, score = match_local_exato_fuzzy(question, df_cat)
    return nome, desc, strat, score

def match_kpi_recurso_local(question: str, instructions_df: pd.DataFrame):
    relevant_df = instructions_df[
        instructions_df["categoria"].str.lower().isin(["kpi", "recurso"])
    ]
    if relevant_df.empty:
        return None, None, 0

    def clean_synonyms(syns_str):
        if isinstance(syns_str, str):
            return [s.strip() for s in syns_str.split(",") if s.strip()]
        return []

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
        syns = clean_synonyms(syns_str)

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
