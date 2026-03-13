import streamlit as st
import gspread
import pandas as pd
import time
from google.oauth2.service_account import Credentials
from datetime import date, time as dtime, datetime, timedelta, timezone

# ======================================================
# 1. CONEXÃO COM GOOGLE SHEETS
# Cria conexão autenticada com a planilha usando
# credenciais armazenadas no Streamlit Secrets.
#
# GOOGLE SHEETS CONNECTION
# Creates an authenticated connection to the
# spreadsheet using credentials stored in secrets.
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

    # Tenta conectar até 5 vezes em caso de erro temporário
    # Retry connection up to 5 times if a temporary error occurs
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
# Lê os registros da planilha e converte para DataFrame.
# O cache reduz chamadas repetidas à API.
#
# DATA LOADING (CACHE)
# Reads spreadsheet records and converts them
# to a Pandas DataFrame. Cache reduces API calls.
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
# Garante que a conexão com a planilha seja criada
# antes de qualquer operação do aplicativo.
#
# INITIALIZE SHEET
# Ensures the spreadsheet connection exists
# before any application operation.
# ======================================================

sheet = connect_sheets()

# ======================================================
# 4. FAKE CURSOR
# Simula comportamento de um cursor de banco SQL
# para permitir uso de SELECT, INSERT e DELETE.
#
# FAKE CURSOR
# Simulates a SQL database cursor to allow
# SELECT, INSERT and DELETE operations.
# ======================================================

class FakeCursor:

    def __init__(self, sheet):
        self.sheet = sheet
        self.result = []

    def execute(self, query, params=None):

        try:

            df = carregar_dados()

            # Executa consulta SELECT retornando os registros
            # Executes SELECT query returning records
            if query.strip().upper().startswith("SELECT"):
                self.result = df.to_dict("records")

            # Remove registro da planilha pelo ID
            # Deletes a row from spreadsheet using ID
            elif query.strip().upper().startswith("DELETE"):

                id_del = params[0]
                rows = self.sheet.get_all_values()

                for i, r in enumerate(rows):
                    if str(r[0]) == str(id_del):
                        self.sheet.delete_rows(i + 1)
                        break

                carregar_dados.clear()

            # Estrutura preparada para futura lógica de UPDATE
            # Structure prepared for future UPDATE logic
            elif query.strip().upper().startswith("UPDATE"):
                pass

            # Insere novo registro na planilha
            # Inserts a new row into the spreadsheet
            elif query.strip().upper().startswith("INSERT"):

                self.sheet.append_row(list(params))
                carregar_dados.clear()

        except Exception as e:
            st.error(f"Erro ao executar operação: {e}")

    # Retorna todos os resultados da consulta
    # Returns all query results
    def fetchall(self):
        return self.result

    # Retorna apenas o primeiro resultado
    # Returns only the first result
    def fetchone(self):
        return self.result[0] if self.result else None


# ======================================================
# 5. FAKE CONN
# Simula conexão de banco para manter padrão
# commit/rollback utilizado em aplicações SQL.
#
# FAKE CONNECTION
# Simulates database connection to keep
# commit/rollback pattern used in SQL apps.
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
# Carrega dados da planilha para o estado da sessão
# evitando leituras repetidas da API.
#
# INITIAL DATA LOAD
# Loads spreadsheet data into session state
# avoiding repeated API reads.
# ======================================================

if "df" not in st.session_state:
    st.session_state.df = carregar_dados()

df = st.session_state.df

# -----------------------------
# ESTADOS E CONFIGURAÇÃO
# Define configurações da página
# e estados globais da aplicação.
#
# APP STATE AND CONFIGURATION
# Defines page settings and
# global application state.
# -----------------------------

st.set_page_config(page_title="Agenda PRCOSET", page_icon="📅", layout="wide")

for key in ["aba_atual", "editando", "evento_id", "msg"]:
    if key not in st.session_state:
        st.session_state[key] = "LISTA" if key == "aba_atual" else None

st.title("📅 Agenda PRCOSET")

# Créditos do desenvolvedor
# Developer credits
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

# Botões de navegação entre lista e formulário
# Navigation buttons between list and form
cm1, cm2, _ = st.columns([1, 1, 4])

if cm1.button("📋 Ver Lista", use_container_width=True):
    st.session_state.aba_atual = "LISTA"
    st.rerun()

if cm2.button("➕ Novo Evento", use_container_width=True):
    st.session_state.aba_atual = "FORM"
    st.session_state.editando = False
    st.session_state.evento_id = None
    st.rerun()

# Exibe mensagem de sucesso após operações
# Displays success message after operations
if st.session_state.msg:
    st.success(st.session_state.msg)
    st.session_state.msg = None

# -----------------------------
# TELA DE FORMULÁRIO
# Tela usada para criar ou editar eventos.
#
# FORM SCREEN
# Screen used to create or edit events.
# -----------------------------
