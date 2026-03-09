import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from datetime import date, time, datetime, timedelta, timezone

# ======================================================
# 1. CONEXÃO COM GOOGLE SHEETS
# ======================================================

@st.cache_resource
def connect_sheets():

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )

    client = gspread.authorize(creds)

    sheet = client.open_by_key(
        "1RRabjIuJA0BbVm5Xq969zMHM9rn0QvBKV8V_txnBNfw"
    ).sheet1

    return sheet


# ======================================================
# 2. CARREGAR DADOS
# ======================================================

sheet = connect_sheets()

def carregar_dados():

    try:
        dados = sheet.get_all_records()
        return pd.DataFrame(dados)

    except Exception as e:
        st.error("Erro ao carregar dados da planilha.")
        st.exception(e)
        return pd.DataFrame()


df = carregar_dados()


# ======================================================
# 3. CONFIG APP
# ======================================================

st.set_page_config(
    page_title="Agenda PRCOSET",
    page_icon="📅",
    layout="wide"
)

for key in ["aba_atual", "editando", "evento_id", "msg"]:
    if key not in st.session_state:
        st.session_state[key] = "LISTA" if key == "aba_atual" else None


st.title("📅 Agenda PRCOSET")


st.markdown(
"""
<div style="
font-size:12px;
color:#777;
margin-top:-10px;
margin-bottom:10px;
padding-bottom:6px;
border-bottom:1px solid #e0e0e0;
">
Aplicativo desenvolvido por
<a href="https://github.com/fredeeerico" target="_blank"
style="text-decoration:none;font-weight:600;color:#2b488e;">
Fred Augusto
</a>
— dúvidas,
<a href="https://wa.me/5562981120444"
target="_blank"
style="color:#2b488e;text-decoration:none;">
clique aqui
</a>
</div>
""",
unsafe_allow_html=True
)

# ======================================================
# MENU
# ======================================================

cm1, cm2, _ = st.columns([1,1,4])

if cm1.button("📋 Ver Lista", use_container_width=True):
    st.session_state.aba_atual = "LISTA"
    st.rerun()

if cm2.button("➕ Novo Evento", use_container_width=True):

    st.session_state.aba_atual = "FORM"
    st.session_state.editando = False
    st.session_state.evento_id = None
    st.rerun()


if st.session_state.msg:
    st.success(st.session_state.msg)
    st.session_state.msg = None


# ======================================================
# FORMULÁRIO
# ======================================================

if st.session_state.aba_atual == "FORM":

    st.subheader("📝 Detalhes do Evento")

    with st.form("form_evento"):

        c_t1, c_t2 = st.columns(2)

        pres_val = c_t1.checkbox("👑 Agenda Presidente?")
        mot_val = c_t2.checkbox("🚗 Precisa Motorista?")

        tit_val = st.text_input("📝 Título")

        c = st.columns(3)

        data_val = c[0].date_input("📅 Data", value=date.today())
        hi_val = c[1].time_input("⏰ Início", value=time(9,0))
        hf_val = c[2].time_input("⏰ Fim", value=time(10,0))

        loc_val = st.text_input("📍 Local")
        end_val = st.text_input("🏠 Endereço")

        cob_val = st.multiselect(
            "🎥 Cobertura",
            ["Redes","Foto","Vídeo","Imprensa"]
        )

        resp_val = st.text_input("👥 Responsáveis")
        eq_val = st.text_input("🎒 Equipamentos")

        obs_val = st.text_area("📝 Observações")

        cmot1, cmot2 = st.columns(2)

        nm_val = cmot1.text_input("Nome Motorista")
        tm_val = cmot2.text_input("Tel Motorista")

        st_val = st.selectbox(
            "Status",
            ["ATIVO","CANCELADO"]
        )

        salvar = st.form_submit_button(
            "💾 SALVAR EVENTO",
            use_container_width=True
        )

        if salvar:

            nova_linha = [

                1 if pres_val else 0,
                tit_val,
                str(data_val),
                hi_val.strftime("%H:%M"),
                hf_val.strftime("%H:%M"),
                loc_val,
                end_val,
                ", ".join(cob_val),
                resp_val,
                eq_val,
                obs_val,
                1 if mot_val else 0,
                nm_val,
                tm_val,
                st_val
            ]

            sheet.append_row(nova_linha)

            st.session_state.msg = "💾 Evento salvo com sucesso!"
            st.session_state.aba_atual = "LISTA"

            st.rerun()


# ======================================================
# LISTAGEM
# ======================================================

elif st.session_state.aba_atual == "LISTA":

    df = carregar_dados()

    if df.empty:
        st.info("Nenhum evento encontrado.")
        st.stop()

    with st.expander("🔍 FILTRAR BUSCA", expanded=False):

        f_col1, f_col2, f_col3 = st.columns(3)

        filtro_data = f_col1.date_input(
            "Filtrar por Data",
            value=None
        )

        filtro_tipo = f_col2.selectbox(
            "Tipo de Agenda",
            ["Todas","Agenda do Presidente","Outras Agendas"]
        )

        filtro_equipe = f_col3.text_input(
            "Buscar por Responsável"
        )

    for i, ev in df.iterrows():

        d_dt = datetime.strptime(
            str(ev["data"]),
            "%Y-%m-%d"
        ).date()

        if filtro_data and d_dt != filtro_data:
            continue

        if filtro_tipo == "Agenda do Presidente" and ev["agenda_presidente"] != 1:
            continue

        if filtro_tipo == "Outras Agendas" and ev["agenda_presidente"] == 1:
            continue

        if filtro_equipe and filtro_equipe.lower() not in str(ev["responsaveis"]).lower():
            continue

        cor_base = "#2b488e" if ev["agenda_presidente"] == 1 else "#109439"

        st.markdown(
f"""
<div style="background:{cor_base};
color:white;
padding:22px;
border-radius:15px;
margin-bottom:15px;">

<h3 style="margin:0;">
{'👑' if ev['agenda_presidente']==1 else '📌'} {ev['titulo']}
</h3>

<div style="margin-top:10px;">

<b>📅 {d_dt.strftime('%d/%m/%Y')}</b>
| ⏰ {ev['hora_inicio']} às {ev['hora_fim']}<br>

📍 <b>Local:</b> {ev['local']}<br>

🏠 <b>Endereço:</b> {ev['endereco']}<br>

🎥 <b>Cobertura:</b> {ev['cobertura']}<br>

👥 <b>Equipe:</b> {ev['responsaveis']}<br>

🎒 <b>Equipamentos:</b> {ev['equipamentos']}

</div>

<div style="margin-top:12px;
background:rgba(255,255,255,0.15);
padding:10px;
border-radius:8px;">

<b>📝 Observações:</b>
{ev['observacoes'] if ev['observacoes'] else "Sem observações"}

</div>

</div>
""",
unsafe_allow_html=True
)
