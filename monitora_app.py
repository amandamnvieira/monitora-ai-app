import streamlit as st
import json
from google.cloud import bigquery
from google.oauth2 import service_account
from datetime import datetime

# ─── CONFIG ────────────────────────────────────────────────────────────────────
SENHA = "monitora2026"
PROJECT = "azos-data-analytics"
DATASET = "operacional"
TABELA  = f"`{PROJECT}.{DATASET}.monitoraai_avaliacoes`"

st.set_page_config(
    page_title="MonitoraAI — Revisões",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── ESTILO ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background: #0f172a; color: #f1f5f9; }

.card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 20px 24px;
    margin-bottom: 12px;
    cursor: pointer;
    transition: all 0.2s;
}
.card:hover {
    background: rgba(255,255,255,0.06);
    border-color: rgba(99,102,241,0.4);
}
.tag-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 500;
}
.nota-alta  { color: #4ade80; }
.nota-media { color: #fbbf24; }
.nota-baixa { color: #f87171; }
.resumo-ia {
    background: rgba(99,102,241,0.08);
    border: 1px solid rgba(99,102,241,0.2);
    border-radius: 12px;
    padding: 14px 16px;
    margin-bottom: 16px;
    color: #c7d2fe;
    font-size: 13px;
    line-height: 1.6;
}
.msg-agente {
    background: rgba(99,102,241,0.2);
    border: 1px solid rgba(99,102,241,0.3);
    border-radius: 14px 4px 14px 14px;
    padding: 10px 14px;
    margin: 4px 0 4px 60px;
    color: #c7d2fe;
    font-size: 13px;
    line-height: 1.6;
}
.msg-cliente {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 4px 14px 14px 14px;
    padding: 10px 14px;
    margin: 4px 60px 4px 0;
    color: #e2e8f0;
    font-size: 13px;
    line-height: 1.6;
}
.msg-interno {
    background: rgba(245,158,11,0.08);
    border: 1px solid rgba(245,158,11,0.2);
    border-radius: 8px;
    padding: 8px 12px;
    margin: 4px 0;
    color: #fcd34d;
    font-size: 12px;
    font-family: 'DM Mono', monospace;
}
.msg-autor {
    font-size: 10px;
    color: #475569;
    margin-bottom: 3px;
    font-family: 'DM Mono', monospace;
}
.criterio-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    padding: 16px 18px;
    margin-bottom: 12px;
}
.nota-display {
    font-family: 'DM Mono', monospace;
    font-size: 36px;
    font-weight: 700;
}
div[data-testid="stHorizontalBlock"] { gap: 8px; }
.stButton>button {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-family: 'DM Sans', sans-serif !important;
}
.stTextArea>div>div>textarea {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
    font-family: 'DM Sans', sans-serif !important;
}
.stSelectbox>div>div {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    color: #e2e8f0 !important;
}
</style>
""", unsafe_allow_html=True)


# ─── BIGQUERY ──────────────────────────────────────────────────────────────────
@st.cache_resource
def get_bq_client():
    creds_dict = dict(st.secrets["gcp_service_account"])
    credentials = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    return bigquery.Client(credentials=credentials, project=PROJECT)


def buscar_pendentes():
    client = get_bq_client()
    query = f"""
        SELECT
            ticket_id, tag, agente_id, nota_ia, nota_revisada,
            motivo_selecao, status_revisao, ts_abertura,
            resumo_avaliacao, criterios_json, conversa_formatada,
            eliminatorio_acionado, motivo_eliminatorio,
            tipo_endosso, perfil_segurado, tipo_cobertura,
            tipo_duvida_corretor, tema_escalado,
            tipo_situacao_cobranca, tipo_reembolso
        FROM {TABELA}
        WHERE status_revisao = 'pendente'
        ORDER BY created_at DESC
        LIMIT 100
    """
    return client.query(query).to_dataframe()


def salvar_revisao(ticket_id, nota_revisada, criterios_revisados, observacao, revisado_por):
    client = get_bq_client()
    query = f"""
        UPDATE {TABELA}
        SET
            nota_revisada          = {float(nota_revisada)},
            criterios_revisados_json = '{json.dumps(criterios_revisados, ensure_ascii=False).replace("'", "\\'")}',
            observacao_revisao     = '{observacao.replace("'", "\\'")}',
            revisado_por           = '{revisado_por}',
            status_revisao         = 'revisado',
            ts_revisao             = CURRENT_TIMESTAMP()
        WHERE ticket_id = '{ticket_id}'
    """
    job = client.query(query)
    job.result()
    return True


# ─── UTILS ────────────────────────────────────────────────────────────────────
def parse_json(s, fallback=None):
    if fallback is None:
        fallback = []
    try:
        return json.loads(s) if s else fallback
    except Exception:
        return fallback


def nota_cor(nota):
    if nota >= 80:
        return "nota-alta"
    if nota >= 60:
        return "nota-media"
    return "nota-baixa"


def calcular_nota(criterios):
    total = 0
    for c in criterios:
        nota = c.get("nota", 3)
        peso = c.get("peso", 0)
        fator = {3: 0, 2: 0.1, 1: 0.5, 0: 1.0}.get(int(nota), 0)
        total += peso * fator
    return max(0, round(100 - total))


def tag_cor(tag):
    if "corretor" in tag:
        return "#3b82f6"
    if "segurado" in tag:
        return "#8b5cf6"
    if "cobran" in tag:
        return "#f59e0b"
    return "#6b7280"


def motivo_label(motivo):
    return {"nota_baixa": "🔴 Nota baixa", "nota_alta": "🟢 Nota alta", "amostra_aleatoria": "🔵 Amostra"}.get(motivo, motivo)


def renderizar_conversa(texto):
    if not texto:
        st.markdown("*Conversa não disponível*")
        return
    blocos = texto.replace("\n\n---\n\n", "\n[SEP]\n").split("\n")
    for linha in blocos:
        if linha.strip() == "[SEP]" or linha.strip() == "":
            continue
        if linha.startswith("[AGENTE]"):
            import re
            m = re.match(r"\[AGENTE\]\s*(.*?)\s*\(([^)]+)\):\s*(.*)", linha, re.DOTALL)
            if m:
                autor, ts, msg = m.groups()
                st.markdown(f'<div class="msg-autor" style="text-align:right">{autor} · {ts[:16].replace("T"," ")}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="msg-agente">{msg.strip()}</div>', unsafe_allow_html=True)
        elif linha.startswith("[CLIENTE]") or linha.startswith("[SISTEMA]"):
            import re
            m = re.match(r"\[(\w+)\]\s*(.*?)\s*\(([^)]+)\):\s*(.*)", linha, re.DOTALL)
            if m:
                tipo, autor, ts, msg = m.groups()
                st.markdown(f'<div class="msg-autor">{autor} · {ts[:16].replace("T"," ")}</div>', unsafe_allow_html=True)
                css = "msg-cliente" if tipo == "CLIENTE" else "msg-interno"
                st.markdown(f'<div class="{css}">{msg.strip()}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="msg-interno">{linha}</div>', unsafe_allow_html=True)


# ─── ESTADO ───────────────────────────────────────────────────────────────────
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "tela" not in st.session_state:
    st.session_state.tela = "fila"
if "avaliacao_atual" not in st.session_state:
    st.session_state.avaliacao_atual = None
if "criterios_edit" not in st.session_state:
    st.session_state.criterios_edit = []
if "reload_fila" not in st.session_state:
    st.session_state.reload_fila = 0


# ─── TELA LOGIN ───────────────────────────────────────────────────────────────
if not st.session_state.autenticado:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align:center; margin-bottom:32px">
            <div style="font-size:40px; margin-bottom:12px">🔍</div>
            <h1 style="color:#f1f5f9; font-size:24px; font-weight:600; margin:0">MonitoraAI</h1>
            <p style="color:#64748b; font-size:13px; margin:6px 0 0">Revisão de avaliações de atendimento</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login"):
            senha = st.text_input("Senha de acesso", type="password", placeholder="••••••••••••")
            entrar = st.form_submit_button("Entrar", use_container_width=True)
            if entrar:
                if senha == SENHA:
                    st.session_state.autenticado = True
                    st.rerun()
                else:
                    st.error("Senha incorreta. Tente novamente.")
    st.stop()


# ─── TELA FILA ────────────────────────────────────────────────────────────────
if st.session_state.tela == "fila":
    # Header
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown("""
        <div style="display:flex; align-items:center; gap:12px; padding:8px 0 24px">
            <div style="width:40px;height:40px;border-radius:12px;background:linear-gradient(135deg,#6366f1,#8b5cf6);display:flex;align-items:center;justify-content:center;font-size:20px">🔍</div>
            <div>
                <div style="color:#f1f5f9;font-size:18px;font-weight:600">MonitoraAI</div>
                <div style="color:#64748b;font-size:12px">Fila de revisões pendentes</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col_h2:
        if st.button("↻ Atualizar"):
            st.session_state.reload_fila += 1
            st.cache_data.clear()
            st.rerun()

    # Buscar dados
    with st.spinner("Carregando avaliações..."):
        try:
            df = buscar_pendentes()
        except Exception as e:
            st.error(f"Erro ao conectar ao BigQuery: {e}")
            st.stop()

    if df.empty:
        st.markdown("""
        <div style="text-align:center; padding:80px 0; color:#475569">
            <div style="font-size:48px; margin-bottom:16px">✓</div>
            <p style="font-size:16px">Nenhuma avaliação pendente</p>
        </div>
        """, unsafe_allow_html=True)
        st.stop()

    # Filtros
    col_f1, col_f2, col_f3 = st.columns([2, 2, 3])
    with col_f1:
        tags_disponiveis = ["Todos"] + sorted(df["tag"].unique().tolist())
        filtro_tag = st.selectbox("Ficha", tags_disponiveis, key="filtro_tag")
    with col_f2:
        motivos_disponiveis = ["Todos"] + sorted(df["motivo_selecao"].dropna().unique().tolist())
        filtro_motivo = st.selectbox("Motivo", motivos_disponiveis, key="filtro_motivo")

    # Aplicar filtros
    df_filtrado = df.copy()
    if filtro_tag != "Todos":
        df_filtrado = df_filtrado[df_filtrado["tag"] == filtro_tag]
    if filtro_motivo != "Todos":
        df_filtrado = df_filtrado[df_filtrado["motivo_selecao"] == filtro_motivo]

    st.markdown(f"<p style='color:#64748b; font-size:13px; margin:8px 0 16px'>{len(df_filtrado)} avaliação(ões) encontrada(s)</p>", unsafe_allow_html=True)

    # Lista
    for _, row in df_filtrado.iterrows():
        nota = int(row.get("nota_ia", 0) or 0)
        cor_classe = nota_cor(nota)
        tag = row.get("tag", "")
        motivo = row.get("motivo_selecao", "")
        ticket_id = str(row.get("ticket_id", ""))
        agente = str(row.get("agente_id", ""))
        ts = str(row.get("ts_abertura", ""))[:10]

        col_nota, col_info, col_btn = st.columns([1, 6, 1.5])
        with col_nota:
            st.markdown(f"""
            <div style="text-align:center; padding:12px 0">
                <div class="nota-display {cor_classe}">{nota}</div>
                <div style="font-size:10px; color:#475569; margin-top:2px">nota IA</div>
            </div>
            """, unsafe_allow_html=True)
        with col_info:
            st.markdown(f"""
            <div style="padding:14px 0">
                <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px; flex-wrap:wrap">
                    <span style="font-family:'DM Mono',monospace; font-size:13px; color:#94a3b8">#{ticket_id}</span>
                    <span style="background:{tag_cor(tag)}22; color:{tag_cor(tag)}; padding:2px 10px; border-radius:20px; font-size:11px; font-weight:500">{tag.replace("_"," ")}</span>
                    <span style="font-size:12px; color:#64748b">{motivo_label(motivo)}</span>
                </div>
                <div style="font-size:12px; color:#64748b">
                    Agente: <span style="color:#94a3b8; font-family:'DM Mono',monospace">{agente}</span>
                    &nbsp;&nbsp;·&nbsp;&nbsp;Abertura: {ts}
                </div>
            </div>
            """, unsafe_allow_html=True)
        with col_btn:
            st.markdown("<div style='padding-top:14px'>", unsafe_allow_html=True)
            if st.button("Revisar →", key=f"btn_{ticket_id}"):
                st.session_state.avaliacao_atual = row.to_dict()
                st.session_state.criterios_edit = parse_json(row.get("criterios_json", "[]"), [])
                st.session_state.tela = "revisao"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<hr style='border:none;border-top:1px solid rgba(255,255,255,0.05);margin:4px 0'>", unsafe_allow_html=True)


# ─── TELA REVISÃO ─────────────────────────────────────────────────────────────
elif st.session_state.tela == "revisao":
    av = st.session_state.avaliacao_atual
    if not av:
        st.session_state.tela = "fila"
        st.rerun()

    ticket_id  = str(av.get("ticket_id", ""))
    tag        = av.get("tag", "")
    agente_id  = str(av.get("agente_id", ""))
    nota_ia    = int(av.get("nota_ia", 0) or 0)
    resumo_raw = av.get("resumo_avaliacao", "[]")
    resumo     = parse_json(resumo_raw, [resumo_raw])[0] if resumo_raw else ""
    conversa   = av.get("conversa_formatada", "")
    criterios  = st.session_state.criterios_edit

    nota_revisada = calcular_nota(criterios)

    # Header
    col_v, col_info_h, col_nota_h, col_salvar = st.columns([1, 4, 1.5, 2])
    with col_v:
        if st.button("← Voltar"):
            st.session_state.tela = "fila"
            st.session_state.avaliacao_atual = None
            st.rerun()
    with col_info_h:
        st.markdown(f"""
        <div style="padding:4px 0">
            <div style="display:flex; align-items:center; gap:8px">
                <span style="font-family:'DM Mono',monospace; color:#64748b; font-size:13px">#{ticket_id}</span>
                <span style="background:{tag_cor(tag)}22; color:{tag_cor(tag)}; padding:2px 10px; border-radius:20px; font-size:11px; font-weight:500">{tag.replace("_"," ")}</span>
            </div>
            <div style="font-size:11px; color:#475569; margin-top:4px">Agente: {agente_id}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_nota_h:
        st.markdown(f"""
        <div style="text-align:center; padding:4px 0">
            <div style="font-size:10px; color:#475569; margin-bottom:2px">Nota revisada</div>
            <div class="nota-display {nota_cor(nota_revisada)}">{nota_revisada}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_salvar:
        revisado_por = st.text_input("Seu nome", placeholder="Ex: Ana Lima", label_visibility="collapsed", key="revisado_por")

    st.markdown("<hr style='border:none;border-top:1px solid rgba(255,255,255,0.08);margin:8px 0 20px'>", unsafe_allow_html=True)

    # Duas colunas
    col_conv, col_aval = st.columns([1, 1], gap="large")

    # Coluna conversa
    with col_conv:
        st.markdown("<h4 style='color:#64748b; font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:12px'>Conversa</h4>", unsafe_allow_html=True)

        if resumo:
            st.markdown(f'<div class="resumo-ia"><strong style="color:#818cf8; font-size:11px; text-transform:uppercase; letter-spacing:0.06em">Resumo da IA</strong><br><br>{resumo}</div>', unsafe_allow_html=True)

        renderizar_conversa(conversa)

    # Coluna avaliação
    with col_aval:
        st.markdown(f"""
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:12px">
            <h4 style="color:#64748b; font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:0.08em; margin:0">Avaliação por critério</h4>
            <span style="font-size:12px; color:#475569">Nota IA: <span style="color:{('#4ade80' if nota_ia>=80 else '#fbbf24' if nota_ia>=60 else '#f87171')}; font-weight:700; font-family:'DM Mono',monospace">{nota_ia}</span></span>
        </div>
        """, unsafe_allow_html=True)

        NOTAS_LABELS = {0: "N0 — Não atendeu", 1: "N1 — Parcial", 2: "N2 — Quase", 3: "N3 — Atendeu"}

        for i, c in enumerate(criterios):
            nome    = c.get("criterio_nome", c.get("nome", f"Critério {i+1}"))
            peso    = c.get("peso", 0)
            nota_c  = int(c.get("nota", c.get("avaliacao", "3") if c.get("avaliacao", "3") not in ["N0","N1","N2","N3","ELIMINATÓRIO"] else {"N0":0,"N1":1,"N2":2,"N3":3,"ELIMINATÓRIO":0}.get(c.get("avaliacao","3"), 3)))
            just    = c.get("justificativa", "")

            st.markdown(f"""
            <div class="criterio-card">
                <div style="display:flex; justify-content:space-between; margin-bottom:10px">
                    <span style="font-size:13px; font-weight:500; color:#e2e8f0">{nome}</span>
                    <span style="font-size:11px; color:#475569">peso {peso}</span>
                </div>
            """, unsafe_allow_html=True)

            nova_nota = st.select_slider(
                f"nota_{i}",
                options=[0, 1, 2, 3],
                value=nota_c,
                format_func=lambda n: NOTAS_LABELS[n],
                label_visibility="collapsed",
                key=f"slider_{ticket_id}_{i}",
            )

            nova_just = st.text_area(
                f"just_{i}",
                value=just,
                placeholder="Justificativa...",
                label_visibility="collapsed",
                key=f"just_{ticket_id}_{i}",
                height=68,
            )

            st.markdown("</div>", unsafe_allow_html=True)

            # Atualiza criterios em session_state
            criterios[i]["nota"] = nova_nota
            criterios[i]["justificativa"] = nova_just

        # Recalcula nota após edições
        nota_revisada_final = calcular_nota(criterios)

        # Observação geral
        st.markdown("<h4 style='color:#64748b; font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:0.08em; margin:20px 0 8px'>Observação geral</h4>", unsafe_allow_html=True)
        observacao = st.text_area(
            "observacao",
            placeholder="Comentários sobre a revisão, contexto adicional ou instruções para o agente...",
            label_visibility="collapsed",
            key=f"obs_{ticket_id}",
            height=100,
        )

        # Nota final resumo
        st.markdown(f"""
        <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:12px; padding:16px 20px; display:flex; align-items:center; justify-content:space-between; margin:16px 0">
            <div>
                <div style="font-size:12px; color:#64748b; margin-bottom:4px">Nota revisada calculada</div>
                <div style="font-size:11px; color:#475569">100 − Σ(peso × fator_nota)</div>
            </div>
            <div class="nota-display {nota_cor(nota_revisada_final)}">{nota_revisada_final}</div>
        </div>
        """, unsafe_allow_html=True)

        # Botão salvar
        nome_revisor = st.session_state.get("revisado_por", "")
        if st.button("✓ Salvar revisão", use_container_width=True, key="btn_salvar"):
            if not nome_revisor.strip():
                st.warning("Preencha seu nome antes de salvar.")
            else:
                with st.spinner("Salvando..."):
                    try:
                        salvar_revisao(
                            ticket_id=ticket_id,
                            nota_revisada=nota_revisada_final,
                            criterios_revisados=criterios,
                            observacao=observacao,
                            revisado_por=nome_revisor.strip(),
                        )
                        st.success("Revisão salva com sucesso!")
                        import time; time.sleep(1.5)
                        st.session_state.tela = "fila"
                        st.session_state.avaliacao_atual = None
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")
