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

# conexão banco
conn = psycopg2.connect(
    host="localhost",
    database="obra_casa",
    user="postgres",
    password="postgres123"
)

cursor = conn.cursor()

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

    st.sidebar.header("Filtros")

    fase_filtro = st.sidebar.selectbox(
        "Filtrar fase da obra",
        ["Todas", "fundação", "estrutura", "acabamento"]
    )

    mes_filtro = st.sidebar.selectbox(
        "Filtrar mês",
        ["Todos", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
    )

    # consulta principal
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
        cursor.execute(
            """
            SELECT * FROM despesas_obra
            WHERE fase_obra = %s
            AND EXTRACT(MONTH FROM data) = %s
            """,
            (fase_filtro, mes_filtro)
        )

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

    # busca fornecedor
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

    # cards
    col1, col2 = st.columns(2)

    with col1:
        st.metric("💰 Total Geral", f"R$ {df_base['valor'].sum()}")

    with col2:
        st.metric("📄 Quantidade de Registros", len(df_base))

    # orçamento
    orcamento_total = st.number_input(
        "Orçamento total da obra",
        value=300000
    )

    gasto_atual = df_base["valor"].sum()
    saldo = orcamento_total - gasto_atual
    percentual = (gasto_atual / orcamento_total) * 100 if orcamento_total > 0 else 0

    col3, col4 = st.columns(2)

    with col3:
        st.metric("Saldo do orçamento", f"R$ {saldo}")

    with col4:
        st.metric("Percentual usado", f"{percentual:.2f}%")

    if saldo < (orcamento_total * 0.2):
        st.warning("⚠️ Atenção: saldo abaixo de 20% do orçamento")

    # categoria mais cara
    if not df_base.empty:
        categoria_top = df_base.groupby("categoria")["valor"].sum().idxmax()
        valor_top = df_base.groupby("categoria")["valor"].sum().max()

        st.metric(
            "🏆 Categoria mais cara",
            f"{categoria_top} - R$ {valor_top}"
        )

    # fornecedor mais caro
    cursor.execute("""
        SELECT fornecedor, SUM(valor)
        FROM despesas_obra
        GROUP BY fornecedor
        ORDER BY SUM(valor) DESC
        LIMIT 1
    """)

    fornecedor_top = cursor.fetchone()

    if fornecedor_top:
        st.subheader("Fornecedor com maior custo")
        st.write(f"{fornecedor_top[0]} - R$ {fornecedor_top[1]}")

    # gráfico mensal
    cursor.execute("""
        SELECT EXTRACT(MONTH FROM data), SUM(valor)
        FROM despesas_obra
        GROUP BY EXTRACT(MONTH FROM data)
        ORDER BY EXTRACT(MONTH FROM data)
    """)

    grafico_mes = cursor.fetchall()
    df_mes = pd.DataFrame(grafico_mes, columns=["Mês", "Total"])

    st.subheader("Gastos por mês")
    st.line_chart(df_mes.set_index("Mês"))

    # top categorias
    cursor.execute("""
        SELECT categoria, SUM(valor)
        FROM despesas_obra
        GROUP BY categoria
        ORDER BY SUM(valor) DESC
        LIMIT 5
    """)

    top_categorias = cursor.fetchall()
    df_top = pd.DataFrame(top_categorias, columns=["Categoria", "Total"])

    st.subheader("Top 5 categorias mais caras")
    st.bar_chart(df_top.set_index("Categoria"))

    # gráfico fase
    st.subheader("Distribuição por fase da obra")

    cursor.execute("""
        SELECT fase_obra, SUM(valor)
        FROM despesas_obra
        GROUP BY fase_obra
    """)

    pizza = cursor.fetchall()

    df_pizza = pd.DataFrame(
        pizza,
        columns=["Fase", "Total"]
    )

    st.bar_chart(df_pizza.set_index("Fase"))

# ---------------- GESTÃO ----------------
with aba3:
    st.header("Gestão de dados")

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