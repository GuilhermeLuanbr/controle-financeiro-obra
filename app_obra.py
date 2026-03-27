import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime

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

        cursor.execute("SELECT DISTINCT categoria FROM despesas_obra ORDER BY categoria")
        categorias_db = [linha[0] for linha in cursor.fetchall() if linha[0]]

        categoria_filtro = st.sidebar.multiselect(
            "Filtrar categoria",
            categorias_db
        )

        cursor.execute("SELECT DISTINCT fornecedor FROM despesas_obra ORDER BY fornecedor")
        fornecedores_db = [linha[0] for linha in cursor.fetchall() if linha[0]]

        fornecedor_filtro = st.sidebar.multiselect(
            "Filtrar fornecedor",
            fornecedores_db
        )

        query = """
            SELECT * FROM despesas_obra
            WHERE data BETWEEN %s AND %s
        """
        params = [data_inicio, data_fim]

        if fase_filtro != "Todas":
            query += " AND fase_obra = %s"
            params.append(fase_filtro)

        if categoria_filtro:
            placeholders = ", ".join(["%s"] * len(categoria_filtro))
            query += f" AND categoria IN ({placeholders})"
            params.extend(categoria_filtro)

        if fornecedor_filtro:
            placeholders = ", ".join(["%s"] * len(fornecedor_filtro))
            query += f" AND fornecedor IN ({placeholders})"
            params.extend(fornecedor_filtro)

        query += " ORDER BY data DESC"

        cursor.execute(query, params)
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

        st.subheader("🔎 Resumo do filtro aplicado")

        filtros_ativos = {
            "Período": f"{data_inicio} até {data_fim}",
            "Fase": fase_filtro,
            "Categorias": ", ".join(categoria_filtro) if categoria_filtro else "Todas",
            "Fornecedores": ", ".join(fornecedor_filtro) if fornecedor_filtro else "Todos"
        }

        st.json(filtros_ativos)

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
        # download CSV
        arquivo = df_base.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="📂 Baixar CSV",
            data=arquivo,
            file_name="despesas_obra.csv",
            mime="text/csv"
        )

        # -------- EDITAR DESPESA --------
        st.subheader("✏️ Editar despesa")

        id_editar = st.number_input("ID para editar", min_value=1, step=1, key="id_editar")

        if st.button("Carregar despesa"):
            cursor.execute("""
                SELECT data, categoria, descricao, valor, fornecedor, fase_obra, forma_pagamento
                FROM despesas_obra
                WHERE id = %s
            """, (id_editar,))
            despesa = cursor.fetchone()

            if despesa:
                st.session_state["despesa_edicao"] = {
                    "id": id_editar,
                    "data": despesa[0],
                    "categoria": despesa[1],
                    "descricao": despesa[2],
                    "valor": float(despesa[3]),
                    "fornecedor": despesa[4],
                    "fase_obra": despesa[5],
                    "forma_pagamento": despesa[6]
                }
            else:
                st.warning("ID não encontrado.")

        if "despesa_edicao" in st.session_state:
            desp = st.session_state["despesa_edicao"]

            nova_data = st.date_input("Nova data", value=desp["data"], key="edit_data")
            nova_categoria = st.text_input("Nova categoria", value=desp["categoria"], key="edit_categoria")
            nova_descricao = st.text_input("Nova descrição", value=desp["descricao"], key="edit_descricao")
            novo_valor = st.number_input("Novo valor", value=desp["valor"], key="edit_valor")
            novo_fornecedor = st.text_input("Novo fornecedor", value=desp["fornecedor"], key="edit_fornecedor")

            nova_fase = st.selectbox(
                "Nova fase da obra",
                ["fundação", "estrutura", "acabamento"],
                index=["fundação", "estrutura", "acabamento"].index(desp["fase_obra"]) if desp["fase_obra"] in ["fundação", "estrutura", "acabamento"] else 0,
                key="edit_fase"
            )

            novo_pagamento = st.selectbox(
                "Nova forma de pagamento",
                ["pix", "dinheiro", "cartão", "boleto"],
                index=["pix", "dinheiro", "cartão", "boleto"].index(desp["forma_pagamento"]) if desp["forma_pagamento"] in ["pix", "dinheiro", "cartão", "boleto"] else 0,
                key="edit_pagamento"
            )

            if st.button("Atualizar despesa"):
                cursor.execute("""
                    UPDATE despesas_obra
                    SET data = %s,
                        categoria = %s,
                        descricao = %s,
                        valor = %s,
                        fornecedor = %s,
                        fase_obra = %s,
                        forma_pagamento = %s
                    WHERE id = %s
                """, (
                    nova_data,
                    nova_categoria,
                    nova_descricao,
                    novo_valor,
                    novo_fornecedor,
                    nova_fase,
                    novo_pagamento,
                    desp["id"]
                ))
                conn.commit()
                st.success("Despesa atualizada com sucesso!")
                del st.session_state["despesa_edicao"]

        # -------- EXCLUIR --------
        st.subheader("🗑️ Excluir despesa")

        id_excluir = st.number_input("ID para excluir", step=1, key="id_excluir")

        if st.button("Excluir despesa"):
            cursor.execute(
                "DELETE FROM despesas_obra WHERE id = %s",
                (id_excluir,)
            )
            conn.commit()
            st.success("Despesa excluída!")
