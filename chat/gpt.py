import json
import streamlit as st
from langchain_openai import ChatOpenAI

def analyze_context_with_gpt(user_input, current_context, instructions_df, username="USUARIO"):
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, max_tokens=1000)
    system_prompt = f"""
    Você é um assistente que detecta mudança de assunto.
    O usuário se chama {username}.
    Se o usuário disser algo como 'mudar de assunto', 'trocar de tópico', 'novo tópico', 'qualquer outro assunto', retorne 'novo tópico'.
    Caso contrário, retorne 'continuar'.

    user_input: {user_input}
    current_context: {current_context}
    """
    response = llm.invoke(system_prompt).content.strip().lower()
    if any(kw in response for kw in ["novo tópico","mudar de assunto","trocar de tópico"]):
        return True, "Ok, vamos iniciar um novo tópico."
    return False, "Continuando no mesmo fluxo."

def fallback_gpt_data(question: str, instructions_df, username="USUARIO"):
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
    O usuário se chama {username}.
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

def fallback_gpt_generic_category(category: str, question: str, instructions_df, username="USUARIO"):
    df_cat = instructions_df[instructions_df["categoria"].str.lower() == category.lower()]
    if df_cat.empty:
        return None, None, None, 0

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
    system_prompt = f"""
    Você é um assistente que recebe uma lista de itens da categoria '{category}'.
    O usuário se chama {username}.
    Tente adivinhar se ele se refere a alguma dessas linhas,
    ou retorne {{ "nome_coluna": null, "descricao": null, "estrategia_resposta": null }} se não conseguir.
    """
    user_prompt = f"User input: {question}\nLista de itens da categoria '{category}':\n{knowledge_list}\n"
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
            return None, None, None, 0
        # Retorna score “1” só para constar
        return category, nm, ds, 1
    except:
        return None, None, None, 0

def generate_generic_response(nome: str, desc: str, strat: str, username="USUARIO") -> str:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.9, max_tokens=1000)
    system_prompt = f"Você é um assistente criativo. O usuário se chama {username}."
    user_prompt = f"""
    O usuário busca informação sobre '{nome}'.
    Descrição: '{desc}'.
    Estratégia (não revelar!): '{strat}'.

    - Use a descrição para informar.
    - Aplique a estratégia (se for 'engraçada', faça piadas), sem exibir a estratégia literal.
    - Seja criativa e clara.
    """
    msgs = [
        {"role":"system","content":system_prompt},
        {"role":"user","content":user_prompt}
    ]
    response = llm.invoke(msgs).content.strip()
    return response
