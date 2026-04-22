import os
import calendar
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

st.set_page_config(
    page_title="Jarvis",
    page_icon="💰",
    layout="wide",
)

CATEGORIAS = [
    "Alimentação", "Transporte", "Moradia", "Saúde", "Lazer",
    "Vestuário", "Educação", "Pet", "Tecnologia", "Serviços", "Outros",
]

CORES_CATEGORIA = {
    "Alimentação": "#FF6B6B",
    "Transporte": "#4ECDC4",
    "Moradia": "#45B7D1",
    "Saúde": "#96CEB4",
    "Lazer": "#FFEAA7",
    "Vestuário": "#DDA0DD",
    "Educação": "#98D8C8",
    "Pet": "#F7DC6F",
    "Tecnologia": "#82E0AA",
    "Serviços": "#AEB6BF",
    "Outros": "#D7DBDD",
}

ALTURA_GRAFICO = 300


@st.cache_resource
def get_supabase():
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])


def carregar_gastos(data_inicio: str, data_fim: str, categorias: list) -> pd.DataFrame:
    query = (
        get_supabase()
        .table("gastos")
        .select("*")
        .gte("data", data_inicio)
        .lte("data", data_fim)
    )
    if categorias:
        query = query.in_("categoria", categorias)

    dados = query.order("data", desc=True).execute().data
    if not dados:
        return pd.DataFrame(columns=["id", "valor", "data", "estabelecimento", "categoria", "criado_em"])

    df = pd.DataFrame(dados)
    df["data"] = pd.to_datetime(df["data"])
    df["valor"] = df["valor"].astype(float)
    return df


# ─── Sidebar: Filtros ────────────────────────────────────────────────────────

st.sidebar.title("🔍 Filtros")

tipo_periodo = st.sidebar.radio("Período", ["Mês/Ano", "Intervalo de datas"])

hoje = date.today()

if tipo_periodo == "Mês/Ano":
    col1, col2 = st.sidebar.columns(2)
    with col1:
        mes_sel = st.selectbox(
            "Mês", range(1, 13), index=hoje.month - 1,
            format_func=lambda m: calendar.month_abbr[m].capitalize(),
        )
    with col2:
        ano_sel = st.number_input("Ano", min_value=2020, max_value=hoje.year + 1,
                                  value=hoje.year, step=1)
    ultimo_dia = calendar.monthrange(int(ano_sel), mes_sel)[1]
    data_inicio = f"{int(ano_sel)}-{mes_sel:02d}-01"
    data_fim = f"{int(ano_sel)}-{mes_sel:02d}-{ultimo_dia}"
else:
    intervalo = st.sidebar.date_input(
        "Intervalo",
        value=(date(hoje.year, 1, 1), hoje),
        max_value=hoje,
    )
    data_inicio = str(intervalo[0])
    data_fim = str(intervalo[1]) if len(intervalo) == 2 else str(hoje)

categorias_sel = st.sidebar.multiselect(
    "Categorias", options=CATEGORIAS, default=CATEGORIAS,
)

# ─── Carregar dados ──────────────────────────────────────────────────────────

df = carregar_gastos(data_inicio, data_fim, categorias_sel)

# ─── Cabeçalho ───────────────────────────────────────────────────────────────

st.markdown("## 💰 Jarvis Financeiro — Controle e Registro de Gastos")
st.caption(f"Período: {data_inicio} a {data_fim}")

if df.empty:
    st.info("Nenhum gasto registrado no período selecionado.")
    st.stop()

# ─── Cards de resumo ─────────────────────────────────────────────────────────

total = df["valor"].sum()
categoria_top = df.groupby("categoria")["valor"].sum().idxmax()
estabelecimento_top = df["estabelecimento"].value_counts().idxmax()

c1, c2, c3 = st.columns(3)
c1.metric("💸 Total no período", f"R$ {total:_.2f}".replace("_", ".").replace(".", ",", 1)[::-1].replace(",", ".", 1)[::-1])
c2.metric("🏷️ Maior categoria", categoria_top)
c3.metric("📍 Local mais frequente", estabelecimento_top)

st.divider()

# ─── Linha do tempo  +  Pizza  ───────────────────────────────────────────────

col_linha, col_pizza = st.columns([3, 2])

with col_linha:
    st.markdown("**📈 Gastos por mês**")
    df_mensal = (
        df.assign(mes=df["data"].dt.to_period("M"))
        .groupby("mes")["valor"].sum()
        .reset_index().sort_values("mes")
    )
    df_mensal["mes"] = df_mensal["mes"].dt.strftime("%b/%Y")
    df_mensal.columns = ["Mês", "Total (R$)"]
    fig_linha = px.line(df_mensal, x="Mês", y="Total (R$)", markers=True,
                        height=ALTURA_GRAFICO, category_orders={"Mês": df_mensal["Mês"].tolist()})
    fig_linha.update_traces(line_color="#4ECDC4", marker_size=7)
    fig_linha.update_layout(margin=dict(t=10, b=10), hovermode="x unified",
                            xaxis_type="category")
    st.plotly_chart(fig_linha, use_container_width=True)

with col_pizza:
    st.markdown("**🏷️ Por categoria (%)**")
    df_cat = df.groupby("categoria")["valor"].sum().reset_index()
    df_cat.columns = ["Categoria", "Total (R$)"]
    df_cat = df_cat.sort_values("Total (R$)", ascending=False)
    fig_pizza = px.pie(df_cat, values="Total (R$)", names="Categoria",
                       color="Categoria", color_discrete_map=CORES_CATEGORIA,
                       hole=0.35, height=ALTURA_GRAFICO)
    fig_pizza.update_traces(textposition="inside", textinfo="percent+label",
                            textfont_size=11)
    fig_pizza.update_layout(showlegend=False, margin=dict(t=10, b=10))
    st.plotly_chart(fig_pizza, use_container_width=True)

# ─── Barras  +  Tabela de estabelecimentos ───────────────────────────────────

col_barras, col_tabela = st.columns([2, 3])

with col_barras:
    st.markdown("**📊 Valor por categoria**")
    fig_barras = px.bar(df_cat, x="Total (R$)", y="Categoria", orientation="h",
                        color="Categoria", color_discrete_map=CORES_CATEGORIA,
                        text_auto=".2f", height=ALTURA_GRAFICO)
    fig_barras.update_layout(showlegend=False, margin=dict(t=10, b=10),
                             yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig_barras, use_container_width=True)

with col_tabela:
    st.markdown("**📍 Estabelecimentos**")
    df_estab = (
        df.groupby("estabelecimento")
        .agg(Total=("valor", "sum"), Compras=("valor", "count"))
        .reset_index()
    )
    df_estab["Ticket Médio"] = df_estab["Total"] / df_estab["Compras"]
    df_estab.columns = ["Estabelecimento", "Total (R$)", "Nº Compras", "Ticket Médio (R$)"]
    df_estab = df_estab.sort_values("Total (R$)", ascending=False).reset_index(drop=True)
    st.dataframe(
        df_estab.style.format({"Total (R$)": "R$ {:.2f}", "Ticket Médio (R$)": "R$ {:.2f}"}),
        use_container_width=True,
        hide_index=True,
        height=ALTURA_GRAFICO,
    )
