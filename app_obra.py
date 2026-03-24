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

        mes_filtro = st.sidebar.selectbox(
            "Filtrar mês",
            ["Todos", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
        )

        if fase_filtro == "Todas" and mes_filtro == "Todos":
            cursor.execute("SELECT * FROM despesas_obra")

        elif fase_filtro != "Todas" and mes_filtro == "Todos":
            cursor.execute(
                "SELECT * FROM despesas_obra WHERE fase_obra = %s",
                (fase_filtro,)
            )

        elif fase_filtro == "Todas" and mes_filtro != "Todos":
            cursor.execute(
                "SELECT * FROM despesas_obra WHERE EXTRACT(MONTH FROM data) = %s",
                (mes_filtro,)
            )

        else:
            cursor.execute("""
                SELECT * FROM despesas_obra
                WHERE fase_obra = %s
                AND EXTRACT(MONTH FROM data) = %s
            """, (fase_filtro, mes_filtro))

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

        col1, col2 = st.columns(2)

        with col1:
            st.metric("💰 Total Geral", f"R$ {df_base['valor'].sum()}")

        with col2:
            st.metric("📄 Quantidade de Registros", len(df_base))

# ---------------- GESTÃO ----------------
with aba3:
    st.header("Gestão de dados")

    if banco_ok:
        if st.button("Exportar para Excel"):
            nome_arquivo = f"despesas_obra_{datetime.now().strftime('%d%m%Y_%H%M')}.xlsx"
            df_base.to_excel(nome_arquivo, index=False)
            st.success(f"Arquivo {nome_arquivo} criado!")

        id_excluir = st.number_input("ID para excluir", step=1)

        if st.button("Excluir despesa"):
            cursor.execute(
                "DELETE FROM despesas_obra WHERE id = %s",
                (id_excluir,)
            )
            conn.commit()
            st.success("Despesa excluída!")
