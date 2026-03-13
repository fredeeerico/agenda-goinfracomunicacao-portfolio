import streamlit as st
import gspread
import pandas as pd
import time
from google.oauth2.service_account import Credentials
from datetime import date, time as dtime, datetime, timedelta, timezone

# ======================================================
# 1. CONEXÃO COM GOOGLE SHEETS
# Responsável por autenticar e criar a conexão com a planilha.
#
# GOOGLE SHEETS CONNECTION
# Responsible for authenticating and creating
# the connection with the spreadsheet.
# ======================================================

@st.cache_resource(show_spinner=False)
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

    for tentativa in range(5):
        try:
            sheet = client.open_by_key(
                "1RRabjIuJA0BbVm5Xq969zMHM9rn0QvBKV8V_txnBNfw"
            ).sheet1
            return sheet
        except Exception as e:
            if tentativa == 4:
                st.error("Erro ao conectar ao Google Sheets.")
                raise e
            time.sleep(2)

# ======================================================
# 2. CARREGAMENTO DE DADOS (CACHE)
# Carrega os registros da planilha e converte
# para um DataFrame do Pandas.
#
# DATA LOADING (CACHE)
# Loads spreadsheet records and converts
# them into a Pandas DataFrame.
# ======================================================

@st.cache_data(ttl=120)
def carregar_dados():

    sheet = connect_sheets()

    try:
        records = sheet.get_all_records()

        if not records:
            return pd.DataFrame()

        return pd.DataFrame(records)

    except Exception:
        return pd.DataFrame()

# ======================================================
# 3. INICIALIZA PLANILHA
# Inicializa a conexão com a planilha para uso
# nas operações do aplicativo.
#
# INITIALIZE SPREADSHEET
# Initializes the spreadsheet connection
# for application operations.
# ======================================================

sheet = connect_sheets()

# ======================================================
# 4. FAKE CURSOR
# Classe que simula um cursor de banco de dados
# permitindo operações similares a SQL.
#
# FAKE CURSOR
# Class that simulates a database cursor
# allowing SQL-like operations.
# ======================================================

class FakeCursor:

    def __init__(self, sheet):
        self.sheet = sheet
        self.result = []

    def execute(self, query, params=None):

        try:

            df = carregar_dados()

            if query.strip().upper().startswith("SELECT"):
                self.result = df.to_dict("records")

            elif query.strip().upper().startswith("DELETE"):

                id_del = params[0]
                rows = self.sheet.get_all_values()

                for i, r in enumerate(rows):
                    if str(r[0]) == str(id_del):
                        self.sheet.delete_rows(i + 1)
                        break

                carregar_dados.clear()

            elif query.strip().upper().startswith("UPDATE"):
                pass

            elif query.strip().upper().startswith("INSERT"):

                self.sheet.append_row(list(params))
                carregar_dados.clear()

        except Exception as e:
            st.error(f"Erro ao executar operação: {e}")

    def fetchall(self):
        return self.result

    def fetchone(self):
        return self.result[0] if self.result else None


# ======================================================
# 5. FAKE CONN
# Classe que simula uma conexão de banco
# com métodos commit e rollback.
#
# FAKE CONNECTION
# Class that simulates a database connection
# with commit and rollback methods.
# ======================================================

class FakeConn:

    def commit(self):
        pass

    def rollback(self):
        pass


cursor = FakeCursor(sheet)
conn = FakeConn()

# ======================================================
# 6. CARREGAMENTO INICIAL
# Carrega os dados na sessão para evitar
# múltiplas leituras da planilha.
#
# INITIAL DATA LOAD
# Loads data into session state to avoid
# repeated spreadsheet reads.
# ======================================================

if "df" not in st.session_state:
    st.session_state.df = carregar_dados()

df = st.session_state.df

# -----------------------------
# 2. ESTADOS E CONFIGURAÇÃO
# Define estados globais da aplicação
# como navegação e edição de eventos.
#
# APP STATE AND CONFIGURATION
# Defines global application states
# such as navigation and event editing.
# -----------------------------

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

cm1, cm2, _ = st.columns([1, 1, 4])

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

# -----------------------------
# 3. TELA DE FORMULÁRIO
# Interface para criação ou edição
# de eventos da agenda.
#
# EVENT FORM SCREEN
# Interface used to create or edit
# agenda events.
# -----------------------------

# -----------------------------
# 4. TELA DE LISTAGEM
# Exibe os eventos cadastrados
# em formato de cards visuais.
#
# EVENT LIST SCREEN
# Displays registered events
# in visual card format.
# -----------------------------
