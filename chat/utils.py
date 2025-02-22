import re

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
