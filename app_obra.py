import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime

# Ajustes de tela
st.set_page_config(
    page_title="Controle Financeiro da Obra",
    page_icon="🏗️",
    layout="wide"
)

# conexão protegida
try:
    conn = psycopg2.connect(
        host="aws-1-us-east-1.pooler.supabase.com",
        database="postgres",
        user="postgres.fvcbhzsppyuawcajnlbw",
        password=st.secrets["DB_PASSWORD"],
        port="5432"
    )

    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS despesas_obra (
        id SERIAL PRIMARY KEY,
        data DATE,
        categoria TEXT,
        descricao TEXT,
        valor NUMERIC,
        fornecedor TEXT,
        fase_obra TEXT,
        forma_pagamento TEXT
    )
    """)

    conn.commit()
    banco_ok = True

except Exception as e:
    banco_ok = False
    st.error(f"Erro conexão: {e}")

# título
st.title("🏗️ Controle Financeiro da Obra")
st.markdown("---")

st.markdown("""
<style>
div[data-testid="metric-container"] {
    background-color: #f5f5f5;
    border: 1px solid #ddd;
    padding: 15px;
    border-radius: 10px;
}

section[data-testid="stSidebar"] {
    background-color: #f0f2f6;
}
</style>
""", unsafe_allow_html=True)

# abas
aba1, aba2, aba3 = st.tabs(["Cadastro", "Dashboard", "Gestão"])

# ---------------- CADASTRO ----------------
with aba1:
    st.header("Cadastro de despesas")

    if banco_ok:
        data = st.date_input("Data")
        categoria = st.text_input("Categoria")
        descricao = st.text_input("Descrição")
        valor = st.number_input("Valor")
        fornecedor = st.text_input("Fornecedor")

        fase = st.selectbox(
            "Fase da obra",
            ["fundação", "estrutura", "acabamento"]
        )

        pagamento = st.selectbox(
            "Forma de pagamento",
            ["pix", "dinheiro", "cartão", "boleto"]
        )

        if st.button("Salvar"):
            cursor.execute("""
                INSERT INTO despesas_obra
                (data, categoria, descricao, valor, fornecedor, fase_obra, forma_pagamento)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (data, categoria, descricao, valor, fornecedor, fase, pagamento))

            conn.commit()
            st.success("Despesa salva com sucesso!")

# ---------------- DASHBOARD ----------------
with aba2:
    st.header("Dashboard financeiro")

    if banco_ok:
        st.sidebar.header("Filtros")

        fase_filtro = st.sidebar.selectbox(
            "Filtrar fase da obra",
            ["Todas", "fundação", "estrutura", "acabamento"]
        )

        data_inicio = st.sidebar.date_input("Data inicial")
        data_fim = st.sidebar.date_input("Data final")

        if fase_filtro == "Todas":
            cursor.execute("""
                SELECT * FROM despesas_obra
                WHERE data BETWEEN %s AND %s
            """, (data_inicio, data_fim))
        else:
            cursor.execute("""
                SELECT * FROM despesas_obra
                WHERE fase_obra = %s
                AND data BETWEEN %s AND %s
            """, (fase_filtro, data_inicio, data_fim))

        dados = cursor.fetchall()

        df_base = pd.DataFrame(
            dados,
            columns=[
                "id", "data", "categoria", "descricao",
                "valor", "fornecedor", "fase_obra", "forma_pagamento"
            ]
        )

        st.write("Despesas registradas:")
        st.table(df_base)

        fornecedor_busca = st.text_input("Buscar fornecedor")

        if fornecedor_busca:
            filtro = df_base[
                df_base["fornecedor"].str.contains(
                    fornecedor_busca,
                    case=False,
                    na=False
                )
            ]
            st.subheader("Resultado da busca")
            st.table(filtro)

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("💰 Total Geral", f"R$ {df_base['valor'].sum():,.2f}")

        with col2:
            st.metric("📄 Registros", len(df_base))

        with col3:
            media = df_base["valor"].mean() if not df_base.empty else 0
            st.metric("📊 Ticket Médio", f"R$ {media:,.2f}")
    
if not df_base.empty:
    resumo_categoria = df_base.groupby("categoria")["valor"].sum()
    st.subheader("📈 Gastos por categoria")
    st.bar_chart(resumo_categoria)

if not df_base.empty:
    resumo_fase = df_base.groupby("fase_obra")["valor"].sum()
    st.subheader("🏗️ Gastos por fase da obra")
    st.bar_chart(resumo_fase)

if not df_base.empty:
    df_base["mes"] = pd.to_datetime(df_base["data"]).dt.month
    evolucao = df_base.groupby("mes")["valor"].sum()

    st.subheader("📅 Evolução mensal dos gastos")
    st.line_chart(evolucao)

if not df_base.empty:
    top_fornecedores = df_base.groupby("fornecedor")["valor"].sum().sort_values(ascending=False).head(5)

    st.subheader("🏆 Top 5 fornecedores")
    st.bar_chart(top_fornecedores)

col_g1, col_g2 = st.columns(2)

with col_g1:
    if not df_base.empty:
        resumo_categoria = df_base.groupby("categoria")["valor"].sum()
        st.subheader("📈 Gastos por categoria")
        st.bar_chart(resumo_categoria)

with col_g2:
    if not df_base.empty:
        resumo_fase = df_base.groupby("fase_obra")["valor"].sum()
        st.subheader("🏗️ Gastos por fase da obra")
        st.bar_chart(resumo_fase)

col_g3, col_g4 = st.columns(2)

with col_g3:
    if not df_base.empty:
        df_base["mes"] = pd.to_datetime(df_base["data"]).dt.month
        evolucao = df_base.groupby("mes")["valor"].sum()
        st.subheader("📅 Evolução mensal")
        st.line_chart(evolucao)

with col_g4:
    if not df_base.empty:
        top_fornecedores = df_base.groupby("fornecedor")["valor"].sum().sort_values(ascending=False).head(5)
        st.subheader("🏆 Top fornecedores")
        st.bar_chart(top_fornecedores)
# ---------------- GESTÃO ----------------
with aba3:
    st.header("Gestão de dados")

    if banco_ok:
arquivo = df_base.to_csv(index=False).encode("utf-8")

st.download_button(
    label="📂 Baixar CSV",
    data=arquivo,
    file_name="despesas_obra.csv",
    mime="text/csv"
)

        id_excluir = st.number_input("ID para excluir", step=1)

        if st.button("Excluir despesa"):
            cursor.execute(
                "DELETE FROM despesas_obra WHERE id = %s",
                (id_excluir,)
            )
            conn.commit()
            st.success("Despesa excluída!")
