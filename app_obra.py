import streamlit as st
import psycopg2
import pandas as pd
from datetime import date, timedelta

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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS despesas_obra (
        id SERIAL PRIMARY KEY,
        data DATE,
        categoria TEXT,
        descricao TEXT,
        valor NUMERIC,
        fornecedor TEXT,
        fase_obra TEXT,
        forma_pagamento TEXT,
        quem_pagou TEXT
    )
    """)

    cursor.execute("""
    ALTER TABLE despesas_obra
    ADD COLUMN IF NOT EXISTS quem_pagou TEXT
    """)

    conn.commit()
    banco_ok = True

except Exception as e:
    banco_ok = False
    st.error(f"Erro conexão: {e}")

# -------- ESTILO --------
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

# -------- TÍTULO --------
st.title("🏗️ Controle Financeiro da Obra")
st.markdown("---")

aba1, aba2, aba3 = st.tabs(["Cadastro", "Dashboard", "Gestão"])

df_base = pd.DataFrame(
    columns=[
        "id", "data", "categoria", "descricao", "valor",
        "fornecedor", "fase", "pagamento", "quem_pagou"
    ]
)

# ---------------- CADASTRO ----------------
with aba1:
    st.header("Cadastro de despesas")

    if banco_ok:
        pagadores = ["Guilherme", "Esposa", "Conjunto", "Outro"]

        if mobile:
            data = st.date_input("Data")
            categoria = st.text_input("Categoria")
            valor = st.number_input("Valor", min_value=0.0, step=10.0)
            fornecedor = st.text_input("Fornecedor")
            fase = st.selectbox("Fase", ["fundação", "estrutura", "acabamento"])
            pagamento = st.selectbox("Pagamento", ["pix", "dinheiro", "cartão", "boleto"])
            quem_pagou = st.selectbox("Quem pagou", pagadores)
            descricao = st.text_area("Descrição")

        else:
            col1, col2 = st.columns(2)

            with col1:
                data = st.date_input("Data")
                categoria = st.text_input("Categoria")
                valor = st.number_input("Valor", min_value=0.0, step=10.0)
                quem_pagou = st.selectbox("Quem pagou", pagadores)

            with col2:
                fornecedor = st.text_input("Fornecedor")
                fase = st.selectbox("Fase", ["fundação", "estrutura", "acabamento"])
                pagamento = st.selectbox("Pagamento", ["pix", "dinheiro", "cartão", "boleto"])

            descricao = st.text_area("Descrição")

        if st.button("Salvar", key="btn_salvar"):
            cursor.execute("""
                INSERT INTO despesas_obra
                (data, categoria, descricao, valor, fornecedor, fase_obra, forma_pagamento, quem_pagou)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                data,
                categoria,
                descricao,
                valor,
                fornecedor,
                fase,
                pagamento,
                quem_pagou
            ))

            conn.commit()
            st.success("Despesa salva com sucesso!")

# ---------------- DASHBOARD ----------------
with aba2:
    st.header("Dashboard financeiro")

    if banco_ok:
        st.sidebar.header("Filtros")

        hoje = date.today()
        inicio_padrao = hoje - timedelta(days=365)

        fase_filtro = st.sidebar.selectbox(
            "Filtrar fase da obra",
            ["Todas", "fundação", "estrutura", "acabamento"]
        )

        data_inicio = st.sidebar.date_input("Data inicial", value=inicio_padrao)
        data_fim = st.sidebar.date_input("Data final", value=hoje)

        comparar = st.sidebar.checkbox("Comparar com período anterior")

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

        cursor.execute("SELECT DISTINCT quem_pagou FROM despesas_obra ORDER BY quem_pagou")
        pagadores_db = [linha[0] for linha in cursor.fetchall() if linha[0]]

        pagador_filtro = st.sidebar.multiselect(
            "Filtrar quem pagou",
            pagadores_db
        )

        query = """
            SELECT id, data, categoria, descricao, valor, fornecedor, fase_obra, forma_pagamento, quem_pagou
            FROM despesas_obra
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

        if pagador_filtro:
            placeholders = ", ".join(["%s"] * len(pagador_filtro))
            query += f" AND quem_pagou IN ({placeholders})"
            params.extend(pagador_filtro)

        query += " ORDER BY data DESC"

        cursor.execute(query, params)
        dados = cursor.fetchall()

        df_base = pd.DataFrame(
            dados,
            columns=[
                "id", "data", "categoria", "descricao", "valor",
                "fornecedor", "fase", "pagamento", "quem_pagou"
            ]
        )

        if not df_base.empty:
            df_base["valor"] = pd.to_numeric(df_base["valor"], errors="coerce").fillna(0)

        if comparar:
            dias = (data_fim - data_inicio).days
            data_inicio_ant = data_inicio - timedelta(days=dias)
            data_fim_ant = data_inicio

            query_ant = """
                SELECT id, data, categoria, descricao, valor, fornecedor, fase_obra, forma_pagamento, quem_pagou
                FROM despesas_obra
                WHERE data BETWEEN %s AND %s
            """
            params_ant = [data_inicio_ant, data_fim_ant]

            if fase_filtro != "Todas":
                query_ant += " AND fase_obra = %s"
                params_ant.append(fase_filtro)

            if categoria_filtro:
                placeholders_ant = ", ".join(["%s"] * len(categoria_filtro))
                query_ant += f" AND categoria IN ({placeholders_ant})"
                params_ant.extend(categoria_filtro)

            if fornecedor_filtro:
                placeholders_ant = ", ".join(["%s"] * len(fornecedor_filtro))
                query_ant += f" AND fornecedor IN ({placeholders_ant})"
                params_ant.extend(fornecedor_filtro)

            if pagador_filtro:
                placeholders_ant = ", ".join(["%s"] * len(pagador_filtro))
                query_ant += f" AND quem_pagou IN ({placeholders_ant})"
                params_ant.extend(pagador_filtro)

            cursor.execute(query_ant, params_ant)
            dados_ant = cursor.fetchall()

            df_ant = pd.DataFrame(
                dados_ant,
                columns=[
                    "id", "data", "categoria", "descricao", "valor",
                    "fornecedor", "fase", "pagamento", "quem_pagou"
                ]
            )

            if not df_ant.empty:
                df_ant["valor"] = pd.to_numeric(df_ant["valor"], errors="coerce").fillna(0)
        else:
            df_ant = pd.DataFrame()

        st.subheader("Despesas registradas")
        st.dataframe(df_base, use_container_width=True)

        st.subheader("🔎 Resumo do filtro aplicado")

        filtros_ativos = {
            "Período": f"{data_inicio} até {data_fim}",
            "Fase": fase_filtro,
            "Categorias": ", ".join(categoria_filtro) if categoria_filtro else "Todas",
            "Fornecedores": ", ".join(fornecedor_filtro) if fornecedor_filtro else "Todos",
            "Quem pagou": ", ".join(pagador_filtro) if pagador_filtro else "Todos",
            "Comparação": "Ativada" if comparar else "Desativada"
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
            st.dataframe(filtro, use_container_width=True)

        total_atual = df_base["valor"].sum() if not df_base.empty else 0

        if comparar and not df_ant.empty:
            total_ant = df_ant["valor"].sum()
            variacao = ((total_atual - total_ant) / total_ant * 100) if total_ant != 0 else 0
        else:
            variacao = 0

        media = df_base["valor"].mean() if not df_base.empty else 0

        if mobile:
            col1, col2 = st.columns(2)

            with col1:
                st.metric("💰 Total", f"R$ {total_atual:,.2f}", f"{variacao:.2f}%")

            with col2:
                st.metric("📄 Registros", len(df_base))

            st.metric("📊 Ticket Médio", f"R$ {media:,.2f}")

        else:
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("💰 Total Geral", f"R$ {total_atual:,.2f}", f"{variacao:.2f}%")

            with col2:
                st.metric("📄 Registros", len(df_base))

            with col3:
                st.metric("📊 Ticket Médio", f"R$ {media:,.2f}")

        if not df_base.empty:
            if mobile:
                st.subheader("📈 Gastos por categoria")
                st.bar_chart(df_base.groupby("categoria")["valor"].sum())

                st.subheader("🏗️ Gastos por fase")
                st.bar_chart(df_base.groupby("fase")["valor"].sum())

                st.subheader("💳 Comparativo por pagador")
                st.bar_chart(df_base.groupby("quem_pagou")["valor"].sum())

                st.subheader("🏆 Top fornecedores")
                st.bar_chart(
                    df_base.groupby("fornecedor")["valor"]
                    .sum()
                    .sort_values(ascending=False)
                    .head(5)
                )

            else:
                col_g1, col_g2 = st.columns(2)

                with col_g1:
                    st.subheader("📈 Gastos por categoria")
                    st.bar_chart(df_base.groupby("categoria")["valor"].sum())

                with col_g2:
                    st.subheader("🏗️ Gastos por fase")
                    st.bar_chart(df_base.groupby("fase")["valor"].sum())

                col_g3, col_g4 = st.columns(2)

                with col_g3:
                    st.subheader("💳 Comparativo por pagador")
                    st.bar_chart(df_base.groupby("quem_pagou")["valor"].sum())

                with col_g4:
                    st.subheader("🏆 Top fornecedores")
                    st.bar_chart(
                        df_base.groupby("fornecedor")["valor"]
                        .sum()
                        .sort_values(ascending=False)
                        .head(5)
                    )

            st.subheader("📅 Evolução mensal")

            df_base["mes"] = pd.to_datetime(df_base["data"]).dt.to_period("M").astype(str)
            evolucao = df_base.groupby("mes")["valor"].sum()

            st.line_chart(evolucao)

            st.subheader("📊 Resumo por pagador")

            resumo_pagador = df_base.groupby("quem_pagou")["valor"].sum().reset_index()
            resumo_pagador["percentual"] = (
                resumo_pagador["valor"] / resumo_pagador["valor"].sum() * 100
            ).round(2)

            st.dataframe(resumo_pagador, use_container_width=True)

        else:
            st.info("Nenhuma despesa encontrada para os filtros selecionados.")

# ---------------- GESTÃO ----------------
with aba3:
    st.header("Gestão de dados")

    if banco_ok:
        col_a, col_b = st.columns(2)

        with col_a:
            st.subheader("📂 Exportação")

            arquivo = df_base.to_csv(index=False).encode("utf-8")

            st.download_button(
                label="Baixar CSV das despesas",
                data=arquivo,
                file_name="despesas_obra.csv",
                mime="text/csv",
                key="download_csv_gestao"
            )

        with col_b:
            st.subheader("🗑️ Excluir despesa")

            id_excluir_gestao = st.number_input(
                "ID para excluir",
                min_value=1,
                step=1,
                key="id_excluir_gestao"
            )

            if st.button("Excluir despesa", key="btn_excluir_gestao"):
                cursor.execute(
                    "DELETE FROM despesas_obra WHERE id = %s",
                    (id_excluir_gestao,)
                )
                conn.commit()
                st.success("Despesa excluída com sucesso!")

        st.markdown("---")

        st.subheader("✏️ Editar despesa")

        id_editar_gestao = st.number_input(
            "ID para editar",
            min_value=1,
            step=1,
            key="id_editar_gestao"
        )

        if st.button("Carregar despesa", key="btn_carregar_despesa"):
            cursor.execute("""
                SELECT data, categoria, descricao, valor, fornecedor, fase_obra, forma_pagamento, quem_pagou
                FROM despesas_obra
                WHERE id = %s
            """, (id_editar_gestao,))

            despesa = cursor.fetchone()

            if despesa:
                st.session_state["despesa_edicao"] = {
                    "id": id_editar_gestao,
                    "data": despesa[0],
                    "categoria": despesa[1],
                    "descricao": despesa[2],
                    "valor": float(despesa[3]),
                    "fornecedor": despesa[4],
                    "fase": despesa[5],
                    "pagamento": despesa[6],
                    "quem_pagou": despesa[7]
                }
            else:
                st.warning("ID não encontrado.")

        if "despesa_edicao" in st.session_state:
            desp = st.session_state["despesa_edicao"]

            if mobile:
                nova_data = st.date_input("Nova data", value=desp["data"], key="edit_data")
                nova_categoria = st.text_input("Nova categoria", value=desp["categoria"], key="edit_categoria")
                nova_descricao = st.text_area("Nova descrição", value=desp["descricao"], key="edit_descricao")
                novo_valor = st.number_input("Novo valor", value=desp["valor"], key="edit_valor")
                novo_fornecedor = st.text_input("Novo fornecedor", value=desp["fornecedor"], key="edit_fornecedor")

                nova_fase = st.selectbox(
                    "Nova fase",
                    ["fundação", "estrutura", "acabamento"],
                    index=["fundação", "estrutura", "acabamento"].index(desp["fase"]) if desp["fase"] in ["fundação", "estrutura", "acabamento"] else 0,
                    key="edit_fase"
                )

                novo_pagamento = st.selectbox(
                    "Nova forma de pagamento",
                    ["pix", "dinheiro", "cartão", "boleto"],
                    index=["pix", "dinheiro", "cartão", "boleto"].index(desp["pagamento"]) if desp["pagamento"] in ["pix", "dinheiro", "cartão", "boleto"] else 0,
                    key="edit_pagamento"
                )

                novo_quem_pagou = st.selectbox(
                    "Novo pagador",
                    ["Guilherme", "Esposa", "Conjunto", "Outro"],
                    index=["Guilherme", "Esposa", "Conjunto", "Outro"].index(desp["quem_pagou"]) if desp["quem_pagou"] in ["Guilherme", "Esposa", "Conjunto", "Outro"] else 0,
                    key="edit_quem_pagou"
                )

            else:
                col1, col2 = st.columns(2)

                with col1:
                    nova_data = st.date_input("Nova data", value=desp["data"], key="edit_data")
                    nova_categoria = st.text_input("Nova categoria", value=desp["categoria"], key="edit_categoria")
                    nova_descricao = st.text_area("Nova descrição", value=desp["descricao"], key="edit_descricao")
                    novo_valor = st.number_input("Novo valor", value=desp["valor"], key="edit_valor")

                with col2:
                    novo_fornecedor = st.text_input("Novo fornecedor", value=desp["fornecedor"], key="edit_fornecedor")

                    nova_fase = st.selectbox(
                        "Nova fase",
                        ["fundação", "estrutura", "acabamento"],
                        index=["fundação", "estrutura", "acabamento"].index(desp["fase"]) if desp["fase"] in ["fundação", "estrutura", "acabamento"] else 0,
                        key="edit_fase"
                    )

                    novo_pagamento = st.selectbox(
                        "Nova forma de pagamento",
                        ["pix", "dinheiro", "cartão", "boleto"],
                        index=["pix", "dinheiro", "cartão", "boleto"].index(desp["pagamento"]) if desp["pagamento"] in ["pix", "dinheiro", "cartão", "boleto"] else 0,
                        key="edit_pagamento"
                    )

                    novo_quem_pagou = st.selectbox(
                        "Novo pagador",
                        ["Guilherme", "Esposa", "Conjunto", "Outro"],
                        index=["Guilherme", "Esposa", "Conjunto", "Outro"].index(desp["quem_pagou"]) if desp["quem_pagou"] in ["Guilherme", "Esposa", "Conjunto", "Outro"] else 0,
                        key="edit_quem_pagou"
                    )

            if st.button("Atualizar despesa", key="btn_atualizar_despesa"):
                cursor.execute("""
                    UPDATE despesas_obra
                    SET data = %s,
                        categoria = %s,
                        descricao = %s,
                        valor = %s,
                        fornecedor = %s,
                        fase_obra = %s,
                        forma_pagamento = %s,
                        quem_pagou = %s
                    WHERE id = %s
                """, (
                    nova_data,
                    nova_categoria,
                    nova_descricao,
                    novo_valor,
                    novo_fornecedor,
                    nova_fase,
                    novo_pagamento,
                    novo_quem_pagou,
                    desp["id"]
                ))

                conn.commit()
                st.success("Despesa atualizada com sucesso!")
                del st.session_state["despesa_edicao"]
