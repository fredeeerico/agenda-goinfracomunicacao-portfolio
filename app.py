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


sheet = connect_sheets()

# ======================================================
# CURSOR FAKE PARA GOOGLE SHEETS
# ======================================================

class FakeCursor:

    def __init__(self, sheet):
        self.sheet = sheet
        self.result = []

    def execute(self, query, params=None):

        df = pd.DataFrame(self.sheet.get_all_records())

        if query.strip().upper().startswith("SELECT"):
            self.result = df.to_dict("records")

        elif query.strip().upper().startswith("DELETE"):

            id_del = params[0]
            rows = self.sheet.get_all_values()

            for i, r in enumerate(rows):
                if str(r[0]) == str(id_del):
                    self.sheet.delete_rows(i + 1)
                    break

        elif query.strip().upper().startswith("INSERT"):

            self.sheet.append_row(list(params))

    def fetchall(self):
        return self.result

    def fetchone(self):
        return self.result[0] if self.result else None


class FakeConn:

    def commit(self):
        pass

    def rollback(self):
        pass


cursor = FakeCursor(sheet)
conn = FakeConn()

def carregar_dados():
    dados = sheet.get_all_records()
    return pd.DataFrame(dados)

df = carregar_dados()

# ======================================================
# CONFIG
# ======================================================

st.set_page_config(page_title="Agenda PRCOSET", page_icon="📅", layout="wide")

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
style="text-decoration:none; font-weight:600; color:#2b488e;">
Fred Augusto
</a>
— dúvidas, 
<a href="https://wa.me/5562981120444" target="_blank"
style="color:#2b488e; text-decoration:none;">
clique aqui
</a>
</div>
""",
    unsafe_allow_html=True
)

# ======================================================
# MENU SUPERIOR
# ======================================================

cm1, cm2, cm3, _ = st.columns([1,1,1,4])

if cm1.button("📋 Ver Lista", use_container_width=True):
    st.session_state.aba_atual = "LISTA"
    st.rerun()

if cm2.button("📅 Agenda de Hoje", use_container_width=True):
    st.session_state.aba_atual = "HOJE"
    st.rerun()

if cm3.button("➕ Novo Evento", use_container_width=True):
    st.session_state.aba_atual = "FORM"
    st.session_state.editando = False
    st.session_state.evento_id = None
    st.rerun()

if st.session_state.msg:
    st.success(st.session_state.msg)
    st.session_state.msg = None


# ======================================================
# TELA FORMULÁRIO
# ======================================================

if st.session_state.aba_atual == "FORM":

    ev_db = None

    if st.session_state.editando and st.session_state.evento_id:

        cursor.execute(
            "SELECT * FROM eventos WHERE id=%s",
            (st.session_state.evento_id,)
        )

        ev_db = cursor.fetchone()

    with st.form("form_evento"):

        st.subheader("📝 Detalhes do Evento")

        c1, c2 = st.columns(2)

        pres_val = c1.checkbox(
            "👑 Agenda Presidente?",
            value=bool(ev_db["agenda_presidente"]) if ev_db else False
        )

        tit_val = st.text_input(
            "📝 Título",
            value=ev_db["titulo"] if ev_db else ""
        )

        c = st.columns(3)

        data_val = c[0].date_input(
            "📅 Data",
            value=ev_db["data"] if ev_db else date.today()
        )

        hi_val = c[1].time_input(
            "⏰ Início",
            value=ev_db["hora_inicio"] if ev_db else time(9,0)
        )

        hf_val = c[2].time_input(
            "⏰ Fim",
            value=ev_db["hora_fim"] if ev_db else time(10,0)
        )

        loc_val = st.text_input(
            "📍 Local",
            value=ev_db["local"] if ev_db else ""
        )

        end_val = st.text_input(
            "🏠 Endereço",
            value=ev_db["endereco"] if ev_db else ""
        )

        resp_val = st.text_input(
            "👥 Responsáveis",
            value=ev_db["responsaveis"] if ev_db else ""
        )

        obs_val = st.text_area(
            "📝 Observações",
            value=ev_db["observacoes"] if ev_db else ""
        )

        st_val = st.selectbox(
            "Status",
            ["ATIVO","CANCELADO"],
            index=0 if not ev_db or ev_db["status"]=="ATIVO" else 1
        )

        salvar = st.form_submit_button("💾 SALVAR EVENTO",use_container_width=True)

        if salvar:

            dados = (
                1 if pres_val else 0,
                tit_val,
                data_val,
                hi_val,
                hf_val,
                loc_val,
                end_val,
                "",
                resp_val,
                "",
                obs_val,
                0,
                "",
                "",
                st_val,
            )

            cursor.execute("INSERT INTO eventos VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",dados)

            conn.commit()

            st.session_state.aba_atual="LISTA"
            st.session_state.msg="Evento salvo"
            st.rerun()


# ======================================================
# TELA AGENDA DE HOJE
# ======================================================

elif st.session_state.aba_atual == "HOJE":

    st.subheader("📅 Agenda do Dia")

    cursor.execute("SELECT * FROM eventos")
    eventos = cursor.fetchall()

    hoje = datetime.now(timezone(timedelta(hours=-3))).date()

    eventos_hoje = []

    for ev in eventos:

        d_dt = (
            ev["data"]
            if isinstance(ev["data"], date)
            else datetime.strptime(str(ev["data"]), "%Y-%m-%d").date()
        )

        if d_dt == hoje:
            eventos_hoje.append(ev)

    if not eventos_hoje:
        st.info("Nenhum evento para hoje.")

    for ev in eventos_hoje:

        st.markdown(
            f"""
<div style="background:#2b488e;color:white;padding:15px;border-radius:10px;margin-bottom:10px;">
<b>{ev['titulo']}</b><br>
📅 {ev['data']} | ⏰ {ev['hora_inicio']} às {ev['hora_fim']}<br>
📍 {ev['local']}
</div>
""",
            unsafe_allow_html=True
        )


# ======================================================
# LISTA COMPLETA
# ======================================================

elif st.session_state.aba_atual == "LISTA":

    cursor.execute(
        "SELECT * FROM eventos ORDER BY data ASC, hora_inicio ASC"
    )

    eventos = cursor.fetchall()

    if not eventos:
        st.info("Nenhum evento encontrado.")

    for ev in eventos:

        st.markdown(
            f"""
<div style="background:#2b488e;color:white;padding:18px;border-radius:15px;margin-bottom:15px;">
<b>{ev['titulo']}</b><br>
📅 {ev['data']} | ⏰ {ev['hora_inicio']} às {ev['hora_fim']}<br>
📍 {ev['local']}
</div>
""",
            unsafe_allow_html=True
        )
