import os
import calendar
from typing import Optional
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()


def _client():
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])


def salvar_gasto(valor: float, data: str, estabelecimento: str, categoria: str) -> dict:
    resultado = (
        _client()
        .table("gastos")
        .insert({
            "valor": valor,
            "data": data,
            "estabelecimento": estabelecimento,
            "categoria": categoria,
        })
        .execute()
    )
    return resultado.data[0] if resultado.data else None


def buscar_gastos(ano: Optional[int] = None, mes: Optional[int] = None, categoria: Optional[str] = None) -> list:
    query = _client().table("gastos").select("*")

    if ano and mes:
        ultimo_dia = calendar.monthrange(ano, mes)[1]
        query = query.gte("data", f"{ano}-{mes:02d}-01").lte("data", f"{ano}-{mes:02d}-{ultimo_dia}")
    elif ano:
        query = query.gte("data", f"{ano}-01-01").lte("data", f"{ano}-12-31")

    if categoria:
        query = query.eq("categoria", categoria)

    return query.order("data", desc=True).execute().data
