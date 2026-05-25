"""
app.py — Interface principal do Sistema de Redações
CCJ — Câmara Municipal do Rio de Janeiro

Uso: python -m streamlit run app.py
"""

import os
import re
import datetime
import streamlit as st
from io import BytesIO
from pathlib import Path

from harmonizer import (
    Emenda, TipoEmenda, StatusEmenda,
    parsear_emendas_com_ia, harmonizar_texto,
)
from utils import (
    ler_docx, ler_txt, ler_pdf, analisar_estrutura,
    salvar_sessao, listar_sessoes, carregar_sessao,
    exportar_redacao_final_docx, exportar_relatorio_problemas_txt,
)


# ─────────────────────────────────────────────────────────────────────────────
# CHAVE DE API — lê dos Streamlit Secrets, variável de ambiente ou input manual
# ─────────────────────────────────────────────────────────────────────────────

def _resolver_api_key() -> tuple[str, bool]:
    """
    Retorna (api_key, chave_embutida).
    chave_embutida=True quando a chave vem dos Secrets/env (oculta na UI).
    """
    # 1. Streamlit Cloud Secrets
    try:
        key = st.secrets["ANTHROPIC_API_KEY"]
        if key:
            return key, True
    except (KeyError, FileNotFoundError):
        pass
    # 2. Variável de ambiente
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        return key, True
    # 3. Input manual (session state)
    return st.session_state.get("api_key", ""), False

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURAÇÃO DA PÁGINA
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Sistema de Redações — CCJ CMRJ",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
/* Cabeçalho */
.cabecalho {
    background: linear-gradient(135deg, #1a3a5c 0%, #2d6a9f 100%);
    padding: 1.2rem 2rem;
    border-radius: 10px;
    color: white;
    margin-bottom: 1.2rem;
}
.cabecalho h1 { color: white; margin: 0; font-size: 1.8rem; }
.cabecalho p  { color: #c8dff0; margin: 0.3rem 0 0; font-size: 0.95rem; }

/* Cards de emenda */
.card-aprovada   { border-left: 5px solid #28a745; background: #f6fff8; padding: 0.6rem 1rem; border-radius: 0 6px 6px 0; margin-bottom: 4px; }
.card-rejeitada  { border-left: 5px solid #dc3545; background: #fff6f6; padding: 0.6rem 1rem; border-radius: 0 6px 6px 0; margin-bottom: 4px; }
.card-pendente   { border-left: 5px solid #ffc107; background: #fffdf0; padding: 0.6rem 1rem; border-radius: 0 6px 6px 0; margin-bottom: 4px; }
.card-prejudicada{ border-left: 5px solid #6c757d; background: #f8f9fa; padding: 0.6rem 1rem; border-radius: 0 6px 6px 0; margin-bottom: 4px; }

/* Badges */
.badge { display:inline-block; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }
.badge-mod  { background:#cce5ff; color:#004085; }
.badge-sup  { background:#f8d7da; color:#721c24; }
.badge-adi  { background:#d4edda; color:#155724; }
.badge-sub  { background:#fff3cd; color:#856404; }
.badge-agl  { background:#e2d9f3; color:#3d1e8a; }
.badge-out  { background:#e2e3e5; color:#383d41; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# ESTADO DA SESSÃO
# ─────────────────────────────────────────────────────────────────────────────

def init_state():
    defaults = {
        'api_key':           '',
        'nome_projeto':      '',
        'texto_original':    '',
        'emendas':           [],
        'resultado_harm':    None,
        'aba_votacao_ativa': False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# Resolve API key (secrets > env > manual)
_api_key_resolvida, _chave_embutida = _resolver_api_key()
if _chave_embutida:
    st.session_state.api_key = _api_key_resolvida

# Atalhos
api_key          = _api_key_resolvida
nome_projeto     = st.session_state.nome_projeto
texto_original   = st.session_state.texto_original
emendas: list[Emenda] = st.session_state.emendas


# ─────────────────────────────────────────────────────────────────────────────
# CABEÇALHO
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="cabecalho">
  <h1>⚖️ Sistema de Redações</h1>
  <p>Comissão de Constituição, Justiça e Redação — Câmara Municipal do Rio de Janeiro</p>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# BARRA LATERAL
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("⚙️ Configuração")

    if _chave_embutida:
        st.success("✅ API configurada pelo administrador")
    else:
        chave = st.text_input(
            "Chave API Anthropic",
            value=st.session_state.api_key,
            type="password",
            help="Necessária para parsing automático e harmonização",
        )
        if chave != st.session_state.api_key:
            st.session_state.api_key = chave
        if st.session_state.api_key:
            st.success("✅ API configurada")
        else:
            st.warning("⚠️ Informe a chave API")

    st.divider()

    # Painel de estatísticas
    if emendas:
        tot   = len(emendas)
        aprov = sum(1 for e in emendas if e.status == StatusEmenda.APROVADA)
        rejet = sum(1 for e in emendas if e.status == StatusEmenda.REJEITADA)
        prej  = sum(1 for e in emendas if e.status == StatusEmenda.PREJUDICADA)
        pend  = tot - aprov - rejet - prej

        st.header("📊 Painel da Sessão")
        c1, c2 = st.columns(2)
        c1.metric("Total",         tot)
        c2.metric("✅ Aprovadas",   aprov)
        c1.metric("❌ Rejeitadas",  rejet)
        c2.metric("⬜ Pendentes",   pend)
        if prej:
            st.metric("⚠️ Prejudicadas", prej)

        pct = int(aprov / tot * 100) if tot else 0
        st.progress(pct / 100, text=f"Aprovação: {pct}%")

    st.divider()

    # Salvar / Carregar sessão
    st.header("💾 Sessão")

    if st.button("💾 Salvar Sessão", use_container_width=True):
        if texto_original or emendas:
            p = salvar_sessao(nome_projeto, texto_original, emendas)
            st.success(f"Salvo em: {p.name}")
        else:
            st.warning("Nada para salvar.")

    sessoes = listar_sessoes()
    if sessoes:
        opts = {s.name: s for s in sessoes[:10]}
        escolha = st.selectbox("Carregar sessão anterior:", ["—"] + list(opts.keys()))
        if escolha != "—" and st.button("📂 Carregar", use_container_width=True):
            np, to, ems = carregar_sessao(opts[escolha])
            st.session_state.nome_projeto  = np
            st.session_state.texto_original = to
            st.session_state.emendas        = ems
            st.session_state.resultado_harm = None
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# ABAS PRINCIPAIS
# ─────────────────────────────────────────────────────────────────────────────

aba1, aba2, aba3, aba4, aba5 = st.tabs([
    "📄 1 · Projeto",
    "📝 2 · Emendas",
    "🗳️ 3 · Votação",
    "⚖️ 4 · Harmonizar",
    "✅ 5 · Redação Final",
])


# ══════════════════════════════════════════════════════════════════════════════
# ABA 1 — PROJETO ORIGINAL
# ══════════════════════════════════════════════════════════════════════════════

with aba1:
    st.header("Projeto Original")

    c1, c2 = st.columns([1, 1])

    with c1:
        np_input = st.text_input(
            "Identificação do Projeto",
            value=st.session_state.nome_projeto,
            placeholder="Ex: PLC 93/2025 — Plano Diretor",
        )
        if np_input != st.session_state.nome_projeto:
            st.session_state.nome_projeto = np_input

    with c2:
        arq = st.file_uploader("Upload do projeto (.docx, .txt ou .pdf)", type=['docx', 'txt', 'pdf'])
        if arq:
            raw = arq.read()
            if arq.name.endswith('.docx'):
                txt = ler_docx(raw)
            elif arq.name.endswith('.pdf'):
                with st.spinner("Extraindo texto do PDF..."):
                    try:
                        txt = ler_pdf(raw)
                    except ImportError as ex:
                        st.error(str(ex))
                        txt = ""
            else:
                txt = ler_txt(raw)
            if txt:
                st.session_state.texto_original = txt
                st.success(f"✅ '{arq.name}' carregado.")
                if arq.name.endswith('.pdf'):
                    st.info("💡 Verifique o texto abaixo e remova cabeçalhos/rodapés ou seções de "
                            "legislação citada que não façam parte da lei, se necessário.")

    texto_edit = st.text_area(
        "Texto integral do projeto:",
        value=st.session_state.texto_original,
        height=520,
        placeholder="Cole aqui o texto completo do projeto de lei...",
        label_visibility="collapsed",
    )
    if texto_edit != st.session_state.texto_original:
        st.session_state.texto_original = texto_edit
        st.session_state.resultado_harm = None   # invalida harmonização anterior

    if st.session_state.texto_original:
        struct = analisar_estrutura(st.session_state.texto_original)
        st.info(
            f"📋 Estrutura detectada: "
            f"**{struct['artigos']} artigos** · "
            f"**{struct['paragrafos']} parágrafos** · "
            f"**{struct['incisos']} incisos** · "
            f"**{struct['alineas']} alíneas** · "
            f"**{struct['anexos']} anexos**"
        )


# ══════════════════════════════════════════════════════════════════════════════
# ABA 2 — EMENDAS
# ══════════════════════════════════════════════════════════════════════════════

with aba2:
    st.header("Carregamento das Emendas")

    metodo = st.radio(
        "Como deseja adicionar as emendas?",
        ["📋 Colar / Upload em bloco (recomendado para muitas emendas)",
         "➕ Adicionar manualmente uma a uma"],
        horizontal=True,
    )

    if "Colar" in metodo:
        c1, c2 = st.columns([3, 1])
        with c1:
            bulk = st.text_area(
                "Cole aqui o texto completo de todas as emendas:",
                height=320,
                placeholder=(
                    "EMENDA MODIFICATIVA Nº 1\n"
                    "Vereador(a): NOME\n\n"
                    "Altera o art. 5º...\n\n"
                    "EMENDA SUPRESSIVA Nº 2\n"
                    "Suprima-se o art. 12.\n..."
                ),
                key="bulk_emendas",
            )
        with c2:
            arq_em = st.file_uploader(
                "Ou faça upload (.docx/.txt)",
                type=['docx', 'txt'],
                key="upload_emendas",
            )
            if arq_em:
                raw_em = arq_em.read()
                bulk_lido = ler_docx(raw_em) if arq_em.name.endswith('.docx') else ler_txt(raw_em)
                st.session_state['_bulk_lido'] = bulk_lido
                st.success(f"✅ {arq_em.name} carregado")

        # Usa texto do upload se disponível
        texto_emendas_input = st.session_state.get('_bulk_lido') or bulk or ""

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("🤖 Processar com IA", type="primary",
                         disabled=not (texto_emendas_input and api_key),
                         use_container_width=True):
                with st.spinner("Analisando emendas com IA..."):
                    try:
                        novas = parsear_emendas_com_ia(texto_emendas_input, api_key)
                        st.session_state.emendas = novas
                        st.session_state.resultado_harm = None
                        st.success(f"✅ {len(novas)} emendas identificadas!")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Erro: {ex}")

        with col_btn2:
            if st.button("📥 Importar como texto bruto (sem IA)",
                         disabled=not texto_emendas_input,
                         use_container_width=True):
                # Tenta divisão por padrão comum de emendas
                partes = re.split(
                    r'\n(?=EMENDA\s+\w*\s*N[ºo°°]?\s*\d+)',
                    texto_emendas_input,
                    flags=re.IGNORECASE,
                )
                novas = []
                for i, parte in enumerate(partes, 1):
                    parte = parte.strip()
                    if parte:
                        num_m = re.search(r'N[ºo°°]?\s*(\d+)', parte, re.IGNORECASE)
                        novas.append(Emenda(
                            numero=int(num_m.group(1)) if num_m else i,
                            texto_bruto=parte,
                            parseada=False,
                            notas_parse="Importado como texto bruto — verifique tipo e alvo"
                        ))
                novas.sort(key=lambda e: e.numero)
                st.session_state.emendas = novas
                st.success(f"{len(novas)} emendas importadas. Complete tipo/alvo manualmente.")
                st.rerun()

        if not api_key and texto_emendas_input:
            st.info("💡 Configure a chave API na barra lateral para processar automaticamente.")

    else:  # Manual
        with st.form("form_add_emenda", clear_on_submit=True):
            st.subheader("➕ Nova Emenda")
            col1, col2, col3 = st.columns([1, 2, 2])
            num_em = col1.number_input("Nº", min_value=1,
                                       value=max((e.numero for e in emendas), default=0) + 1)
            tipo_em = col2.selectbox("Tipo", [t.value for t in TipoEmenda if t != TipoEmenda.OUTRO])
            alvo_em = col3.text_input("Alvo", placeholder="Art. 5º, §2º")
            autor_em = st.text_input("Autor", placeholder="Nome do vereador")
            texto_em = st.text_area("Texto da emenda", height=150)
            sub = st.form_submit_button("➕ Adicionar", type="primary")
            if sub and texto_em.strip():
                tipo_map = {t.value: t for t in TipoEmenda}
                st.session_state.emendas.append(Emenda(
                    numero=num_em,
                    texto_bruto=texto_em.strip(),
                    tipo=tipo_map.get(tipo_em),
                    alvo=alvo_em.strip() or None,
                    novo_texto=texto_em.strip(),
                    autor=autor_em.strip() or None,
                    parseada=True,
                ))
                st.session_state.emendas.sort(key=lambda e: e.numero)
                st.success(f"Emenda {num_em} adicionada!")
                st.rerun()

    # ── Lista de emendas carregadas ──
    if emendas:
        st.divider()
        st.subheader(f"Emendas carregadas: {len(emendas)}")

        # Ações em lote
        c1, c2, c3 = st.columns(3)
        if c1.button("🗑️ Remover todas", use_container_width=True):
            st.session_state.emendas = []
            st.session_state.resultado_harm = None
            st.rerun()
        if c2.button("🔄 Limpar status (tudo pendente)", use_container_width=True):
            for e in st.session_state.emendas:
                e.status = StatusEmenda.PENDENTE
            st.rerun()

        filtro = st.selectbox("Filtro:", ["Todas", "Pendente", "Aprovada", "Rejeitada", "Prejudicada"])

        nao_parseadas = [e for e in emendas if not e.parseada]
        if nao_parseadas:
            st.warning(
                f"⚠️ {len(nao_parseadas)} emenda(s) importada(s) como texto bruto. "
                "Verifique e ajuste tipo e alvo abaixo."
            )

        tipo_map = {t.value: t for t in TipoEmenda}
        badge_map = {
            TipoEmenda.MODIFICATIVA: "badge-mod",
            TipoEmenda.SUPRESSIVA:   "badge-sup",
            TipoEmenda.ADITIVA:      "badge-adi",
            TipoEmenda.SUBSTITUTIVA: "badge-sub",
            TipoEmenda.AGLUTINATIVA: "badge-agl",
            TipoEmenda.OUTRO:        "badge-out",
        }

        for i, em in enumerate(st.session_state.emendas):
            if filtro != "Todas" and em.status.value != filtro:
                continue

            card_cls = {
                StatusEmenda.APROVADA:    "card-aprovada",
                StatusEmenda.REJEITADA:   "card-rejeitada",
                StatusEmenda.PENDENTE:    "card-pendente",
                StatusEmenda.PREJUDICADA: "card-prejudicada",
            }.get(em.status, "card-pendente")

            tipo_label = em.tipo.value if em.tipo else "?"
            badge_cls  = badge_map.get(em.tipo, "badge-out")
            alvo_str   = f" | {em.alvo}" if em.alvo else ""
            autor_str  = f" | {em.autor}" if em.autor else ""
            status_icon = {"Aprovada":"✅","Rejeitada":"❌","Pendente":"⬜","Prejudicada":"⚠️"}.get(em.status.value,"")

            with st.expander(
                f"{status_icon} Emenda {em.numero} · {tipo_label}{alvo_str}{autor_str}",
                expanded=not em.parseada,
            ):
                st.markdown(f'<span class="badge {badge_cls}">{tipo_label}</span>', unsafe_allow_html=True)

                cc1, cc2 = st.columns([3, 1])
                with cc1:
                    txt_show = em.novo_texto or em.texto_bruto
                    st.text_area("Texto:", value=txt_show, height=120,
                                 key=f"txt_show_{i}", disabled=True)
                    if em.notas_parse:
                        st.info(f"📝 {em.notas_parse}")

                with cc2:
                    # Editar tipo e alvo
                    novo_tipo = st.selectbox(
                        "Tipo:",
                        [t.value for t in TipoEmenda],
                        index=[t.value for t in TipoEmenda].index(
                            em.tipo.value if em.tipo else TipoEmenda.OUTRO.value
                        ),
                        key=f"sel_tipo_{i}",
                    )
                    st.session_state.emendas[i].tipo = tipo_map.get(novo_tipo)

                    novo_alvo = st.text_input("Alvo:", value=em.alvo or "", key=f"alvo_{i}")
                    st.session_state.emendas[i].alvo = novo_alvo or None


# ══════════════════════════════════════════════════════════════════════════════
# ABA 3 — VOTAÇÃO (modo rápido para plenário)
# ══════════════════════════════════════════════════════════════════════════════

with aba3:
    st.header("🗳️ Painel de Votação")
    st.caption("Modo otimizado para uso durante a sessão plenária. Marque cada emenda conforme o resultado da votação.")

    if not emendas:
        st.info("Carregue as emendas na aba 2 para usar o painel de votação.")
    else:
        # Filtros rápidos
        c1, c2, c3, c4, c5 = st.columns(5)
        if c1.button("✅ Todas Aprovadas", use_container_width=True):
            for e in st.session_state.emendas: e.status = StatusEmenda.APROVADA
            st.rerun()
        if c2.button("❌ Todas Rejeitadas", use_container_width=True):
            for e in st.session_state.emendas: e.status = StatusEmenda.REJEITADA
            st.rerun()
        if c3.button("⬜ Limpar tudo", use_container_width=True):
            for e in st.session_state.emendas: e.status = StatusEmenda.PENDENTE
            st.rerun()

        filtro_vot = c4.selectbox("Filtrar:", ["Todas","Pendente","Aprovada","Rejeitada","Prejudicada"],
                                   key="filtro_vot", label_visibility="collapsed")
        busca_vot = c5.text_input("Buscar (art./autor):", key="busca_vot", label_visibility="collapsed",
                                   placeholder="Buscar...")

        st.divider()

        # Tabela compacta
        for i, em in enumerate(st.session_state.emendas):
            # Filtros
            if filtro_vot != "Todas" and em.status.value != filtro_vot:
                continue
            if busca_vot:
                haystack = f"{em.alvo or ''} {em.autor or ''} {em.texto_bruto}".lower()
                if busca_vot.lower() not in haystack:
                    continue

            status_icon = {"Aprovada":"✅","Rejeitada":"❌","Pendente":"⬜","Prejudicada":"⚠️"}.get(em.status.value,"")
            tipo_str = em.tipo.value if em.tipo else "?"
            alvo_str = em.alvo or "—"

            c1, c2, c3, c4, c5 = st.columns([0.8, 1.5, 2.5, 1, 1])
            c1.markdown(f"**{status_icon} {em.numero}**")
            c2.caption(tipo_str)
            c3.caption(alvo_str)

            if c4.button("✅ Aprov.", key=f"v_apr_{i}", use_container_width=True):
                st.session_state.emendas[i].status = StatusEmenda.APROVADA
                st.rerun()
            if c5.button("❌ Rejeit.", key=f"v_rej_{i}", use_container_width=True):
                st.session_state.emendas[i].status = StatusEmenda.REJEITADA
                st.rerun()

            # Expandir para ver texto se necessário
            with st.expander("ver texto", expanded=False):
                txt = em.novo_texto or em.texto_bruto
                st.write(txt[:600] + ("..." if len(txt) > 600 else ""))
                cc1, cc2 = st.columns(2)
                if cc1.button("✅ Aprovada", key=f"vx_apr_{i}"):
                    st.session_state.emendas[i].status = StatusEmenda.APROVADA
                    st.rerun()
                if cc2.button("⚠️ Prejudicada", key=f"vx_pre_{i}"):
                    st.session_state.emendas[i].status = StatusEmenda.PREJUDICADA
                    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# ABA 4 — HARMONIZAÇÃO
# ══════════════════════════════════════════════════════════════════════════════

with aba4:
    st.header("Harmonização do Texto")

    aprovadas_count = sum(1 for e in emendas if e.status == StatusEmenda.APROVADA)

    # Checklist de pré-requisitos
    checks = {
        "Projeto original carregado":     bool(texto_original),
        "Emendas carregadas":             bool(emendas),
        f"Emendas aprovadas ({aprovadas_count})": aprovadas_count > 0,
        "API Key configurada":            bool(api_key),
    }
    all_ok = all(checks.values())

    cc1, cc2 = st.columns([2, 1])
    with cc2:
        st.subheader("Pré-requisitos")
        for label, ok in checks.items():
            st.write(("✅ " if ok else "❌ ") + label)

    with cc1:
        if all_ok:
            st.success(
                f"Pronto para harmonizar **{aprovadas_count} emendas aprovadas** "
                f"sobre o projeto **{nome_projeto or 'sem nome'}**."
            )

            aviso_grande = aprovadas_count > 50
            if aviso_grande:
                st.info(
                    f"ℹ️ {aprovadas_count} emendas aprovadas — o processamento pode levar "
                    "até 2 minutos. Aguarde."
                )

            if st.button(
                f"🔄 Harmonizar agora ({aprovadas_count} emendas)",
                type="primary",
                use_container_width=True,
            ):
                with st.spinner(
                    f"Aplicando {aprovadas_count} emendas e harmonizando o texto... aguarde..."
                ):
                    try:
                        resultado = harmonizar_texto(
                            texto_original,
                            emendas,
                            api_key,
                            nome_projeto,
                        )
                        st.session_state.resultado_harm = resultado
                        st.success("✅ Harmonização concluída! Vá para a aba Redação Final.")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Erro na harmonização: {ex}")
        else:
            st.warning("Preencha os pré-requisitos para habilitar a harmonização.")

    # Resultado anterior
    if st.session_state.resultado_harm:
        res = st.session_state.resultado_harm
        st.divider()

        n_absurdos = len(getattr(res, 'alertas_absurdos', []))
        n_erros    = len(res.erros_criticos)
        n_avisos   = len(res.avisos)
        n_mapa     = len(res.mapa_renumeracao)
        n_log      = len(res.log_alteracoes)

        st.subheader("Resultado da última harmonização")

        # ── Nível 1: Absurdo Manifesto ──
        alertas = getattr(res, 'alertas_absurdos', [])
        if alertas:
            st.error(
                f"🔴 {n_absurdos} ABSURDO(S) MANIFESTO(S) — "
                "o texto perdeu completamente o sentido normativo. "
                "A CCJ **deve** intervir com ofício justificado (art. 250, §1º RI)."
            )
            for al in alertas:
                st.markdown(f"> 🔴 {al}")

        # ── Nível 2: Erros Críticos ──
        if res.erros_criticos:
            st.error(
                f"🚨 {n_erros} ERRO(S) CRÍTICO(S) — contradição entre emendas aprovadas. "
                "Recomenda-se reabertura da discussão (art. 250, §2º RI)."
            )
            for e in res.erros_criticos:
                st.markdown(f"> 🚨 {e}")

        # ── Nível 3: Avisos jurídicos ──
        if res.avisos:
            st.warning(
                f"⚠️ {n_avisos} aviso(s) redacional(is) — texto preservado como aprovado. "
                "Correção possível mediante ofício (art. 250, §1º RI)."
            )
            for a in res.avisos:
                st.markdown(f"> ⚠️ {a}")

        if not alertas and not res.erros_criticos and not res.avisos:
            st.success("✅ Nenhum problema jurídico ou redacional detectado!")

        # ── Mapa e Log (operacionais) ──
        if res.mapa_renumeracao:
            with st.expander(f"🔢 Mapa de renumeração ({n_mapa} dispositivos renumerados)"):
                for orig, novo in res.mapa_renumeracao.items():
                    st.write(f"  **{orig}**  →  **{novo}**")

        if res.log_alteracoes:
            with st.expander(f"📋 Log operacional ({n_log} ações registradas) — clique para ver"):
                st.caption(
                    "Registro técnico das operações realizadas. "
                    "Não confundir com os avisos jurídicos acima."
                )
                for item in res.log_alteracoes:
                    st.write(f"• {item}")


# ══════════════════════════════════════════════════════════════════════════════
# ABA 5 — REDAÇÃO FINAL
# ══════════════════════════════════════════════════════════════════════════════

with aba5:
    st.header("Redação Final")

    if not st.session_state.resultado_harm:
        st.info("Execute a harmonização na aba 4 para gerar a redação final.")
    else:
        res = st.session_state.resultado_harm

        if res.erros_criticos:
            st.error(
                "⚠️ Há erros críticos! Verifique a aba de Harmonização. "
                "O art. 250, §2º do RI determina que, nesse caso, a CCJ deve propor "
                "a reabertura da discussão em vez de oferecer redação final."
            )

        st.subheader("📄 Texto Harmonizado")
        st.caption("Você pode editar o texto abaixo antes de exportar.")

        texto_editavel = st.text_area(
            "Redação Final:",
            value=res.texto_harmonizado,
            height=620,
            label_visibility="collapsed",
            key="texto_redacao_final",
        )
        # Atualiza se editado
        if texto_editavel != res.texto_harmonizado:
            st.session_state.resultado_harm.texto_harmonizado = texto_editavel

        st.divider()
        st.subheader("💾 Exportar")

        ec1, ec2, ec3 = st.columns(3)

        # TXT simples
        ec1.download_button(
            label="📄 Baixar .txt",
            data=texto_editavel.encode('utf-8'),
            file_name=f"redacao_final_{re.sub(r'[^\\w]','_',nome_projeto or 'projeto')}.txt",
            mime="text/plain",
            use_container_width=True,
        )

        # DOCX formatado
        docx_bytes = exportar_redacao_final_docx(
            texto=texto_editavel,
            nome_projeto=nome_projeto,
            avisos=res.avisos,
            erros=res.erros_criticos,
            alertas_absurdos=getattr(res, 'alertas_absurdos', []),
            mapa=res.mapa_renumeracao,
            log=res.log_alteracoes,
        )
        ec2.download_button(
            label="📝 Baixar .docx",
            data=docx_bytes,
            file_name=f"redacao_final_{re.sub(r'[^\\w]','_',nome_projeto or 'projeto')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )

        # Relatório de problemas
        _alertas = getattr(res, 'alertas_absurdos', [])
        if res.avisos or res.erros_criticos or _alertas:
            rel_txt = exportar_relatorio_problemas_txt(
                nome_projeto, res.avisos, res.erros_criticos, res.mapa_renumeracao,
                alertas_absurdos=_alertas,
            )
            ec3.download_button(
                label="⚠️ Baixar Relatório de Problemas",
                data=rel_txt.encode('utf-8'),
                file_name=f"problemas_{re.sub(r'[^\\w]','_',nome_projeto or 'projeto')}.txt",
                mime="text/plain",
                use_container_width=True,
            )
