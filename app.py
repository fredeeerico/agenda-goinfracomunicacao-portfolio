import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from datetime import date, time, datetime, timedelta, timezone

# ======================================================
# CONFIGURAÇÃO
# ======================================================

st.set_page_config(
    page_title="Agenda PRCOSET",
    page_icon="📅",
    layout="wide"
)

# ======================================================
# CONEXÃO GOOGLE SHEETS
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


sheet = connect_sheets()

# ======================================================
# CARREGAR DADOS
# ======================================================

def carregar_dados():

    dados = sheet.get_all_records()

    if not dados:
        return pd.DataFrame()

    return pd.DataFrame(dados)


def salvar_evento(dados):

    df = carregar_dados()

    if len(df) == 0:
        novo_id = 1
    else:
        novo_id = int(df["id"].max()) + 1

    linha = [novo_id] + list(dados)

    sheet.append_row(linha)

# ======================================================
# ESTADO DA APLICAÇÃO
# ======================================================

for key in ["aba_atual", "msg"]:
    if key not in st.session_state:
        st.session_state[key] = "LISTA" if key == "aba_atual" else None


df = carregar_dados()

# ======================================================
# CABEÇALHO
# ======================================================

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
<a href="https://github.com/fredeeerico"
target="_blank"
style="text-decoration:none;font-weight:600;color:#2b488e;">
Fred Augusto
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
    st.session_state.aba_atual="LISTA"
    st.rerun()

if cm2.button("➕ Novo Evento", use_container_width=True):
    st.session_state.aba_atual="FORM"
    st.rerun()

# ======================================================
# MENSAGENS
# ======================================================

if st.session_state.msg:
    st.success(st.session_state.msg)
    st.session_state.msg=None

# ======================================================
# FORMULÁRIO
# ======================================================

if st.session_state.aba_atual == "FORM":

    with st.form("evento"):

        st.subheader("📝 Detalhes do Evento")

        c1,c2=st.columns(2)

        pres=c1.checkbox("👑 Agenda Presidente?")
        mot=c2.checkbox("🚗 Precisa Motorista?")

        titulo=st.text_input("📝 Título")

        c=st.columns(3)

        data=c[0].date_input("📅 Data",value=date.today())
        hi=c[1].time_input("⏰ Início",value=time(9,0))
        hf=c[2].time_input("⏰ Fim",value=time(10,0))

        local=st.text_input("📍 Local")
        endereco=st.text_input("🏠 Endereço")

        cobertura=st.multiselect(
            "🎥 Cobertura",
            ["Redes","Foto","Vídeo","Imprensa"]
        )

        responsaveis=st.text_input("👥 Responsáveis")
        equipamentos=st.text_input("🎒 Equipamentos")
        observacoes=st.text_area("📝 Observações")

        m1,m2=st.columns(2)

        motorista_nome=m1.text_input("Nome Motorista")
        motorista_tel=m2.text_input("Tel Motorista")

        status=st.selectbox(
            "Status",
            ["ATIVO","CANCELADO"]
        )

        salvar=st.form_submit_button(
            "💾 SALVAR EVENTO",
            use_container_width=True
        )

        if salvar:

            dados=(
                1 if pres else 0,
                titulo,
                str(data),
                hi.strftime("%H:%M"),
                hf.strftime("%H:%M"),
                local,
                endereco,
                ", ".join(cobertura),
                responsaveis,
                equipamentos,
                observacoes,
                1 if mot else 0,
                motorista_nome,
                motorista_tel,
                status
            )

            salvar_evento(dados)

            st.session_state.msg="Evento salvo!"
            st.session_state.aba_atual="LISTA"
            st.rerun()

# ======================================================
# LISTAGEM
# ======================================================

elif st.session_state.aba_atual=="LISTA":

    if df.empty:
        st.info("Nenhum evento encontrado.")
        st.stop()

    agora_dt=datetime.now(
        timezone(timedelta(hours=-3))
    ).replace(tzinfo=None)

    hoje=agora_dt.date()
    hora_agora_str=agora_dt.time().strftime("%H:%M")

    def formatar_hora(v):

        try:
            return str(v)[:5]
        except:
            return "00:00"

    for _,ev in df.sort_values(
        ["data","hora_inicio"]
    ).iterrows():

        d_dt=datetime.strptime(
            str(ev["data"]),
            "%Y-%m-%d"
        ).date()

        cor="#2b488e" if ev["agenda_presidente"]==1 else "#109439"

        st.markdown(f"""
<div style="
background:{cor};
color:white;
padding:22px;
border-radius:15px;
margin-bottom:15px;
">

<h3>
{'👑' if ev['agenda_presidente']==1 else '📌'}
{ev['titulo']}
</h3>

<b>📅 {d_dt.strftime('%d/%m/%Y')}</b>
| ⏰ {formatar_hora(ev['hora_inicio'])}
às {formatar_hora(ev['hora_fim'])}

<br>

📍 {ev['local']}

<br>

👥 {ev['responsaveis']}

</div>
""",unsafe_allow_html=True)
