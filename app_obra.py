import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime

# -------- CONFIG --------
st.set_page_config(
    page_title="Controle Financeiro da Obra",
    page_icon="🏗️",
    layout="centered"
)

# -------- LOGIN --------
if "logado" not in st.session_state:
    st.session_state["logado"] = False

if not st.session_state["logado"]:
    st.title("🔐 Login")

    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if usuario == "admin" and senha == "1234":
            st.session_state["logado"] = True
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")

    st.stop()

# -------- MOBILE --------
mobile = st.sidebar.checkbox("📱 Modo Mobile")

# -------- CONEXÃO --------
try:
    conn = psycopg2.connect(
        host="aws-1-us-east-1.pooler.supabase.com",
        database="postgres",
        user="postgres.fvcbhzsppyuawcajnlbw",
        password=st.secrets["DB_PASSWORD"],
        port="5432"
    )
    cursor = conn.cursor()
    banco_ok = True
except:
    banco_ok = False
    st.warning("Banco offline")

# -------- TÍTULO --------
st.title("🏗️ Controle Financeiro da Obra")
st.markdown("---")

# -------- ABAS --------
aba1, aba2, aba3 = st.tabs(["Cadastro", "Dashboard", "Gestão"])

# ---------------- CADASTRO ----------------
with aba1:
    st.header("Cadastro de despesas")

    if banco_ok:

        if mobile:
            data = st.date_input("Data")
            categoria = st.text_input("Categoria")
            valor = st.number_input("Valor")

            fornecedor = st.text_input("Fornecedor")
            fase = st.selectbox("Fase", ["fundação", "estrutura", "acabamento"])
            pagamento = st.selectbox("Pagamento", ["pix", "dinheiro", "cartão", "boleto"])

            descricao = st.text_area("Descrição")

        else:
            col1, col2 = st.columns(2)

            with col1:
                data = st.date_input("Data")
                categoria = st.text_input("Categoria")
                valor = st.number_input("Valor")

            with col2:
                fornecedor = st.text_input("Fornecedor")
                fase = st.selectbox("Fase", ["fundação", "estrutura", "acabamento"])
                pagamento = st.selectbox("Pagamento", ["pix", "dinheiro", "cartão", "boleto"])

            descricao = st.text_area("Descrição")

        if st.button("Salvar"):
            cursor.execute("""
                INSERT INTO despesas_obra
                (data, categoria, descricao, valor, fornecedor, fase_obra, forma_pagamento)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (data, categoria, descricao, valor, fornecedor, fase, pagamento))

            conn.commit()
            st.success("Despesa salva!")

# ---------------- DASHBOARD ----------------
with aba2:
    st.header("Dashboard")

    if banco_ok:
        st.sidebar.header("Filtros")

        data_inicio = st.sidebar.date_input("Data inicial")
        data_fim = st.sidebar.date_input("Data final")

        cursor.execute("SELECT * FROM despesas_obra WHERE data BETWEEN %s AND %s", (data_inicio, data_fim))
        dados = cursor.fetchall()

        df = pd.DataFrame(dados, columns=[
            "id","data","categoria","descricao","valor","fornecedor","fase","pagamento"
        ])

        total = df["valor"].sum()
        media = df["valor"].mean() if not df.empty else 0

        if mobile:
            col1, col2 = st.columns(2)

            with col1:
                st.metric("Total", f"R$ {total:,.2f}")
            with col2:
                st.metric("Registros", len(df))

            st.metric("Ticket Médio", f"R$ {media:,.2f}")

        else:
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Total", f"R$ {total:,.2f}")
            with col2:
                st.metric("Registros", len(df))
            with col3:
                st.metric("Ticket Médio", f"R$ {media:,.2f}")

        if mobile:
            st.bar_chart(df.groupby("categoria")["valor"].sum())
            st.bar_chart(df.groupby("fase")["valor"].sum())
        else:
            col1, col2 = st.columns(2)

            with col1:
                st.bar_chart(df.groupby("categoria")["valor"].sum())
            with col2:
                st.bar_chart(df.groupby("fase")["valor"].sum())

# ---------------- GESTÃO ----------------
with aba3:
    st.header("Gestão")

    if banco_ok:

        arquivo = df.to_csv(index=False).encode("utf-8")

        st.download_button(
            "📂 Baixar CSV",
            arquivo,
            "despesas.csv"
        )

        st.markdown("---")

        id_excluir = st.number_input("ID excluir", min_value=1, key="id_excluir_unico")

        if st.button("Excluir"):
            cursor.execute("DELETE FROM despesas_obra WHERE id = %s", (id_excluir,))
            conn.commit()
            st.success("Excluído")
