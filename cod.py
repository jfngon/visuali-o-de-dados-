import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import networkx as nx
import os

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(
    page_title="Painel de Visualização Orçamentária", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# NOME DO ARQUIVO CONSOLIDADO
ARQUIVO_CSV = 'empenho.csv'

@st.cache_data
def carregar_dados():
    if not os.path.exists(ARQUIVO_CSV):
        st.error(f"Arquivo '{ARQUIVO_CSV}' não encontrado.")
        return None
    
    # Carregamento com encoding para dados do governo
    df = pd.read_csv(ARQUIVO_CSV, sep=';', encoding='latin-1')
    
    # Limpeza de colunas duplicadas para evitar erro de 'Series'
    df = df.loc[:, ~df.columns.duplicated()]
    
    # Mapeamento único para evitar colunas duplicadas após renomear
    mapeado = {}
    regras = [
        ('DATA', 'Data'),
        ('SUPERIOR', 'Orgao_Superior'),
        ('FAVORECIDO', 'Fornecedor'),
        ('VALOR', 'Valor')
    ]

    for busca, destino in regras:
        for col in df.columns:
            if busca in str(col).upper() and destino not in mapeado.values():
                mapeado[col] = destino
                break 

    df = df.rename(columns=mapeado)
    
    # Filtro explícito para manter apenas o necessário e leve
    colunas_uteis = ['Data', 'Orgao_Superior', 'Fornecedor', 'Valor']
    df = df[colunas_uteis].copy()

    # Limpeza e conversão do Valor para numérico
    if 'Valor' in df.columns:
        df['Valor'] = df['Valor'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).str.strip()
        df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce').fillna(0)

    # Conversão da Data
    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
    
    return df

df = carregar_dados()

if df is not None:
    st.title("📊 Gestão e Visualização de Indicadores Orçamentários")
    st.sidebar.header("Navegação do Projeto")
    
    menu = st.sidebar.radio("Selecione a Unidade:", 
                           ["🏠 Resumo Geral", 
                            "📅 Temporal", 
                            "📊 Comparativo", 
                            "🌳 Hierárquico", 
                            "🕸️ Redes e Conexões"])

    # --- ABA: RESUMO GERAL ---
    if menu == "🏠 Resumo Geral":
            st.subheader("Indicadores Consolidados")

        mapa_orgao = {}
        if os.path.exists('lista_codigo.csv'):
            df_cod = pd.read_csv('lista_codigo.csv', sep=';', encoding='latin-1', header=0)
            df_cod.columns = [c.strip().lower() for c in df_cod.columns]
            col_codigo = 'codigo' if 'codigo' in df_cod.columns else df_cod.columns[0]
            col_orgao = 'orgao_superior' if 'orgao_superior' in df_cod.columns else df_cod.columns[1]
            mapa_orgao = dict(zip(df_cod[col_codigo].astype(str).str.strip(), df_cod[col_orgao]))

        df_resumo = df.copy()
        df_resumo['Orgao_Superior'] = df_resumo['Orgao_Superior'].astype(str).str.strip().map(mapa_orgao).fillna(df_resumo['Orgao_Superior'])

        val_total = float(df_resumo['Valor'].sum())
        n_orgaos = int(df_resumo['Orgao_Superior'].nunique())
        n_fornec = int(df['Fornecedor'].nunique())
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Volume Total Empenhado", f"R$ {val_total:,.2f}")
        c2.metric("Total de Órgãos", n_orgaos)
        c3.metric("Total de Fornecedores", n_fornec)
        
        df_ordenado = df.copy()
        df_ordenado['Data_fmt'] = df_ordenado['Data'].dt.strftime('%d/%m/%Y')

        df_ordenado = df_ordenado.sort_values(
            ['Orgao_Superior', 'Data', 'Fornecedor', 'Valor'],
            ascending=[True, True, True, False]
        )


        df_ordenado['data_fmt'] = pd.to_datetime(df_ordenado['Data'], errors='coerce').dt.strftime('%d/%m/%Y')
        df_ordenado = df_ordenado.reset_index(drop=True).rename_axis('posicao').reset_index()
        df_ordenado['valor_correspondente'] = df_ordenado['Valor']
        
        colunas_saida = [
            'posicao' if 'posicao' in df_ordenado.columns else None,
            'Data',
            'Orgao_Superior',
            'valor_correspondente',
            'Fornecedor',
            'Valor',
            'data_fmt'
        ]
        colunas_saida = [c for c in colunas_saida if c is not None]

        if 'data_fmt' in df_ordenado.columns:
            df_ordenado['data_fmt'] = pd.to_datetime(df_ordenado['data_fmt'], errors='coerce').dt.strftime('%d/%m/%Y')

        df_ordenado['data_fornecedor_fmt'] = pd.to_datetime(df_ordenado['Data'], errors='coerce').dt.strftime('%d/%m/%Y')
        df_ordenado['valor_orgao_ref'] = df_ordenado['Valor']

        def br_valor(x):
            try:
                x = float(x)
            except Exception:
                return "0,00"
            s = f"{x:,.2f}"  # 1,234.56
            s = s.replace(',', 'X').replace('.', ',').replace('X', '.')
            return s

        df_ordenado['valor_orgao_ref_fmt'] = df_ordenado['valor_orgao_ref'].apply(br_valor)
        df_ordenado['Valor_fmt'] = df_ordenado['Valor'].apply(br_valor)

        if mapa_orgao:
            df_ordenado['Orgao_Superior'] = (
                df_ordenado['Orgao_Superior'].astype(str).str.strip().map(mapa_orgao).fillna(df_ordenado['Orgao_Superior'])
            )

        colunas_saida_formatadas = [
            'data_fmt',
            'Orgao_Superior',
            'valor_orgao_ref_fmt',
            'Fornecedor',
            'Valor_fmt',
            'data_fornecedor_fmt'
        ]

        df_tabela = df_ordenado[colunas_saida_formatadas].rename(columns={
            'data_fmt': 'Data',
            'Orgao_Superior': 'Orgão',
            'valor_orgao_ref_fmt': 'Valor pago',
            'Fornecedor': 'Fornecedor',
            'Valor_fmt': 'Valor',
            'data_fornecedor_fmt': 'Data de Pagamento'
        })

        st.markdown("**Dados em Formato Tabular**")
        st.dataframe(df_tabela.head(9486), use_container_width=True, height='stretch')


  # --- ABA: (TEMPORAL) ---
    elif menu == "📅 Temporal":
        st.subheader("Evolução Temporal dos Gastos")
        df_t = df.groupby('Data')['Valor'].sum().reset_index().sort_values('Data')
        if not df_t.empty:
            df_t = df_t.sort_values('Data')
            df_t = df_t[df_t['Data'] <= df_t['Data'].max()]


        fig = px.area(df_t, x='Data', y='Valor', title="Fluxo Diário de Empenhos", 
                      color_discrete_sequence=['#1f77b4'])
        st.plotly_chart(fig, use_container_width=True)

    # --- ABA:(COMPARATIVA) ---
    elif menu == "📊 Comparativo":
        st.subheader("Ranking de Investimento por Órgão")
        df_tmp = df.copy()
        df_tmp['Orgao_Superior'] = (
            df_tmp['Orgao_Superior']
            .astype(str)
            .str.replace(r'\.0$', '', regex=True)
            .str.strip()
        )
        df_g = (
            df_tmp.groupby('Orgao_Superior')['Valor']
                  .sum()
                  .sort_values(ascending=False)
                  .reset_index()
                  .head(12)
        )

        df_g_plot = df_g.copy()
        df_g_plot['Valor_milhoes'] = df_g_plot['Valor'] / 1_000_000

        fig = px.bar(
            df_g_plot,
            x='Valor',
            y='Orgao_Superior',
            orientation='h',
            color='Valor',
            text=None,
            custom_data=['Valor_milhoes'],
            title="Top 12 Órgãos por Alocação de Recursos",
            color_continuous_scale='Blues',
        )

        fig.update_layout(
            yaxis={'categoryorder': 'total ascending'},
            showlegend=False,
            height=720,
            margin=dict(l=40, r=20, t=60, b=40),
        )

        fig.update_traces(
            texttemplate='R$ %{customdata[0]}M',
            textposition='outside',
            hovertemplate='Órgão: %{y}<br>Empenhado: R$ %{x:.0f}<extra></extra>'
        )
        st.plotly_chart(fig, use_container_width=True)

        if os.path.exists('lista_codigo.csv'):
            df_cod = pd.read_csv('lista_codigo.csv', sep=';', encoding='latin-1', header=0)
            # Normaliza colunas (caso venha com nomes diferentes/encoding)
            df_cod.columns = [c.strip().lower() for c in df_cod.columns]
            # tenta inferir nomes esperados
            col_codigo = 'codigo' if 'codigo' in df_cod.columns else df_cod.columns[0]
            col_orgao = 'orgao_superior' if 'orgao_superior' in df_cod.columns else df_cod.columns[1]
            mapa_orgao = dict(zip(df_cod[col_codigo].astype(str).str.strip(), df_cod[col_orgao]))
        else:
            mapa_orgao = {}

        st.markdown("#### Top 12 por Órgão")
        df_g_list = df_g.copy().sort_values('Valor', ascending=False)
        for _, r in df_g_list.iterrows():
            codigo = str(r['Orgao_Superior']).strip()
            nome_orgao = mapa_orgao.get(codigo, r['Orgao_Superior'])
            st.write(f"**{nome_orgao}**: R$ {r['Valor']:,.0f}")

    # --- ABA:(HIERÁRQUICA) ---
    elif menu == "🌳 Hierárquico":
        st.subheader("Treemap Hierárquico: Órgão → Fornecedor")

        top_n_org = 15
        top_m_forn_por_org = 12

        df_h = df.copy()
        df_org = df_h.groupby('Orgao_Superior', as_index=False)['Valor'].sum().sort_values('Valor', ascending=False).head(top_n_org)
        orgs = df_org['Orgao_Superior'].tolist()
        df_h = df_h[df_h['Orgao_Superior'].isin(orgs)]
        df_h = (
            df_h.sort_values('Valor', ascending=False)
                .groupby('Orgao_Superior')
                .head(top_m_forn_por_org)
        )

        df_tm = (
            df_h.groupby(['Orgao_Superior', 'Fornecedor'], as_index=False)['Valor'].sum()
        )

        fig = px.treemap(
            df_tm,
            path=['Orgao_Superior', 'Fornecedor'],
            values='Valor',
            color='Valor',
            color_continuous_scale='Viridis',
            title='Distribuição Hierárquica de Recursos'
        )

        fig.update_traces(
            textinfo='label+value',
            hovertemplate='%{label}<br>Valor: R$ %{value:,.0f}<extra></extra>'
        )

        st.plotly_chart(fig, use_container_width=True)
        
        # --- Seção da Tabela/Lista de Órgãos ---
        st.markdown("### Lista de Referência dos Top 15 no Ranking de Empenhos")

        if os.path.exists('lista_codigo.csv'):
            df_cod = pd.read_csv('lista_codigo.csv', sep=';', encoding='latin-1', header=0)
            df_cod.columns = [c.strip().lower() for c in df_cod.columns]
            
            col_codigo = 'codigo' if 'codigo' in df_cod.columns else df_cod.columns[0]
            col_orgao = 'orgao_superior' if 'orgao_superior' in df_cod.columns else df_cod.columns[1]

            orgs_exibidos = df_tm['Orgao_Superior'].unique()
            
            df_lista_final = pd.DataFrame({'codigo_str': [str(x).strip() for x in orgs_exibidos]})
            df_cod['codigo_str'] = df_cod[col_codigo].astype(str).str.strip()
            
            df_lista_final = df_lista_final.merge(df_cod[['codigo_str', col_orgao]], on='codigo_str', how='left')
            
            df_lista_final[col_orgao] = df_lista_final[col_orgao].fillna(df_lista_final['codigo_str'])
            
            df_lista_final['exibicao'] = df_lista_final['codigo_str'] + " — " + df_lista_final[col_orgao]

            lista_texto = "\n\n".join(df_lista_final['exibicao'].tolist())
            
            st.markdown(lista_texto)

        else:
            st.caption("Arquivo lista_codigo.csv não encontrado.")
    
    # --- ABA:(REDES) ---

    elif menu == "🕸️ Redes e Conexões":
        st.subheader("Grafo de Relacionamento Institucional")

        def _norm_codigo(x):
            return (
                str(x)
                .replace('.0', '')
                .replace(' ', '')
                .strip()
            )

        df_net_base = df.copy()
        df_net_base['Orgao_Superior'] = df_net_base['Orgao_Superior'].apply(_norm_codigo)
        df_net = (
            df_net_base.groupby(['Orgao_Superior', 'Fornecedor'], as_index=False)['Valor']
            .sum()
            .sort_values('Valor', ascending=False)
        )

        n_edges = 25
        q = 0.6
        threshold = df_net['Valor'].quantile(q) if len(df_net) else 0
        df_net = df_net[df_net['Valor'] >= threshold].head(n_edges)

        if df_net.empty:
            st.caption("Sem dados suficientes para montar o grafo.")
            st.stop()

        mapa_orgao = {}
        if os.path.exists('lista_codigo.csv'):
            df_cod = pd.read_csv('lista_codigo.csv', sep=';', encoding='latin-1', header=0)
            df_cod.columns = [c.strip().lower() for c in df_cod.columns]
            col_codigo = 'codigo' if 'codigo' in df_cod.columns else df_cod.columns[0]
            col_orgao = 'orgao_superior' if 'orgao_superior' in df_cod.columns else df_cod.columns[1]

            df_cod['codigo_norm'] = df_cod[col_codigo].apply(_norm_codigo)
            mapa_orgao = dict(zip(df_cod['codigo_norm'], df_cod[col_orgao].astype(str).str.strip()))

        G = nx.from_pandas_edgelist(
            df_net.assign(orgao_superior=df_net['Orgao_Superior']),
            source='Orgao_Superior',
            target='Fornecedor',
            edge_attr=['Valor', 'orgao_superior']
        )

        pos = nx.spring_layout(G, k=1.2, seed=42)

        edge_x, edge_y = [], []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

        edge_text = []
        for u, v, data in G.edges(data=True):
            edge_text.append(
                f"Orgão Superior: {u}<br>Fornecedor: {v}<br>Valor: R$ {float(data.get('Valor', 0.0)):,.0f}"
            )

        edge_trace = go.Scatter(
            x=edge_x,
            y=edge_y,
            line=dict(width=1, color='#888'),
            hoverinfo='text',
            text=edge_text,
            mode='lines'
        )

        node_total = {n: 0.0 for n in G.nodes()}
        for u, v, data in G.edges(data=True):
            w = float(data.get('Valor', 0.0))
            node_total[u] += w
            node_total[v] += w

        max_total = max(node_total.values()) if node_total else 1.0

        node_x, node_y = [], []
        node_texts = []
        node_hover = []
        node_sizes = []

        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)

            node_norm = _norm_codigo(node) if node is not None else ''
            node_label = mapa_orgao.get(node_norm, str(node).strip())
            val_total = node_total.get(node, 0.0)

            node_texts.append(node_label)
            node_hover.append(f"{node_label}<br>Valor total: R$ {val_total:,.0f}")
            node_sizes.append(10 + 22 * (val_total / max_total) if max_total else 10)

        node_trace = go.Scatter(
            x=node_x,
            y=node_y,
            mode='markers+text',
            hoverinfo='text',
            text=node_texts,
            textposition='middle center',
            textfont=dict(size=10, color='black'),
            hovertext=node_hover,
            marker=dict(
                size=node_sizes,
                color='orange',
                line_width=2,
                opacity=0.9
            )
        )

        fig = go.Figure(
            data=[edge_trace, node_trace],
            layout=go.Layout(
                showlegend=False,
                height=750,
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
            )
        )
        st.plotly_chart(fig, use_container_width=True)

