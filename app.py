import streamlit as st
import gspread
import pandas as pd
import time
from google.oauth2.service_account import Credentials
from datetime import date, time as dtime, datetime, timedelta, timezone

# ======================================================
# 1. CONEXÃO COM GOOGLE SHEETS
# Estabelece conexão autenticada com Google Sheets
# usando Service Account armazenada no Streamlit Secrets.
#
# GOOGLE SHEETS CONNECTION
# Creates an authenticated connection using
# a Service Account stored in Streamlit secrets.
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

    # Tenta conectar até 5 vezes em caso de falha temporária da API
    # Retry connection up to 5 times if API temporarily fails
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
# Busca todos os registros da planilha e converte
# para um DataFrame do Pandas.
#
# DATA LOADING (CACHED)
# Fetches all spreadsheet records and converts
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
# 3. INICIALIZA CONEXÃO COM PLANILHA
# Garante que a planilha esteja conectada antes
# de qualquer operação do aplicativo.
#
# INITIALIZE SHEET CONNECTION
# Ensures sheet connection before app operations.
# ======================================================

sheet = connect_sheets()

# ======================================================
# 4. CURSOR SIMULADO (FAKE CURSOR)
# Simula comportamento de um cursor SQL para permitir
# uso de comandos SELECT / INSERT / DELETE.
#
# FAKE DATABASE CURSOR
# Simulates SQL cursor behavior to support
# SELECT / INSERT / DELETE style operations.
# ======================================================

class FakeCursor:

    def __init__(self, sheet):
        self.sheet = sheet
        self.result = []

    def execute(self, query, params=None):

        try:

            df = carregar_dados()

            # Simula SELECT retornando todos os registros
            # Simulates SELECT returning all records
            if query.strip().upper().startswith("SELECT"):
                self.result = df.to_dict("records")

            # Remove linha da planilha pelo ID
            # Deletes a row from spreadsheet using ID
            elif query.strip().upper().startswith("DELETE"):

                id_del = params[0]
                rows = self.sheet.get_all_values()

                for i, r in enumerate(rows):
                    if str(r[0]) == str(id_del):
                        self.sheet.delete_rows(i + 1)
                        break

                carregar_dados.clear()

            # Placeholder para futura lógica de UPDATE
            # Placeholder for future UPDATE implementation
            elif query.strip().upper().startswith("UPDATE"):
                pass

            # Insere novo registro na planilha
            # Inserts new record into spreadsheet
            elif query.strip().upper().startswith("INSERT"):

                self.sheet.append_row(list(params))
                carregar_dados.clear()

        except Exception as e:
            st.error(f"Erro ao executar operação: {e}")

    # Retorna todos os registros consultados
    # Returns all fetched records
    def fetchall(self):
        return self.result

    # Retorna apenas um registro
    # Returns a single record
    def fetchone(self):
        return self.result[0] if self.result else None


# ======================================================
# 5. CONEXÃO SIMULADA (FAKE CONNECTION)
# Mantém compatibilidade com padrão SQL
# usando commit() e rollback().
#
# FAKE DATABASE CONNECTION
# Keeps SQL-style workflow compatibility.
# ======================================================

class FakeConn:

    def commit(self):
        pass

    def rollback(self):
        pass


cursor = FakeCursor(sheet)
conn = FakeConn()

# ======================================================
# 6. CARREGAMENTO INICIAL DOS DADOS
# Armazena dados na sessão para evitar
# chamadas repetidas à API do Google Sheets.
#
# INITIAL DATA LOAD
# Stores data in session state to avoid
# repeated API requests.
# ======================================================

if "df" not in st.session_state:
    st.session_state.df = carregar_dados()

df = st.session_state.df

# -----------------------------------------------------
# 7. CONFIGURAÇÃO E ESTADO DA APLICAÇÃO
# Define layout da página e estados globais usados
# para navegação e ações do usuário.
#
# APPLICATION CONFIG AND STATE
# Defines page layout and global states used
# for navigation and user actions.
# -----------------------------------------------------

st.set_page_config(page_title="Agenda PRCOSET", page_icon="📅", layout="wide")

for key in ["aba_atual", "editando", "evento_id", "msg"]:
    if key not in st.session_state:
        st.session_state[key] = "LISTA" if key == "aba_atual" else None

st.title("📅 Agenda PRCOSET")

# Créditos do desenvolvedor e suporte
# Developer credits and support links
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

# -----------------------------------------------------
# 8. BOTÕES DE NAVEGAÇÃO
# Permitem alternar entre lista de eventos
# e formulário de criação/edição.
#
# NAVIGATION BUTTONS
# Switch between event list and event form.
# -----------------------------------------------------

cm1, cm2, _ = st.columns([1, 1, 4])
