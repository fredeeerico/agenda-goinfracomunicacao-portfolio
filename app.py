import streamlit as st
import gspread
import pandas as pd
import time
from google.oauth2.service_account import Credentials
from datetime import date, time as dtime, datetime, timedelta, timezone

# ======================================================
# 1. CONEXÃO COM GOOGLE SHEETS
# Responsável por autenticar e criar conexão com a planilha.
#
# GOOGLE SHEETS CONNECTION
# Handles authentication and creates the connection
# with the Google Sheets database.
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

    # Tenta conectar até 5 vezes em caso de erro temporário da API
    # Retry connection up to 5 times in case of temporary API error
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
# Busca os registros da planilha e converte em DataFrame.
#
# DATA LOADING (CACHED)
# Fetches spreadsheet records and converts them
# into a Pandas DataFrame.
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
# Garante que a conexão com a planilha exista
# antes de executar operações no aplicativo.
#
# INITIALIZE SHEET CONNECTION
# Ensures spreadsheet connection before operations.
# ======================================================

sheet = connect_sheets()

# ======================================================
# 4. FAKE CURSOR
# Simula comportamento de um cursor de banco SQL
# permitindo usar comandos SELECT / INSERT / DELETE.
#
# FAKE CURSOR
# Simulates SQL cursor behavior for simple
# database-like operations using Google Sheets.
# ======================================================

class FakeCursor:

    def __init__(self, sheet):
        self.sheet = sheet
        self.result = []

    def execute(self, query, params=None):

        try:

            df = carregar_dados()

            # Simula consulta SELECT retornando os registros
            # Simulates SELECT query returning records
            if query.strip().upper().startswith("SELECT"):
                self.result = df.to_dict("records")

            # Remove um registro da planilha pelo ID
            # Deletes a row from spreadsheet using the ID
            elif query.strip().upper().startswith("DELETE"):

                id_del = params[0]
                rows = self.sheet.get_all_values()

                for i, r in enumerate(rows):
                    if str(r[0]) == str(id_del):
                        self.sheet.delete_rows(i + 1)
                        break

                carregar_dados.clear()

            # Placeholder para futura implementação de UPDATE
            # Placeholder for future UPDATE implementation
            elif query.strip().upper().startswith("UPDATE"):
                pass

            # Insere novo registro na planilha
            # Inserts a new row into the spreadsheet
            elif query.strip().upper().startswith("INSERT"):

                self.sheet.append_row(list(params))
                carregar_dados.clear()

        except Exception as e:
            st.error(f"Erro ao executar operação: {e}")

    # Retorna todos os registros consultados
    # Returns all query results
    def fetchall(self):
        return self.result

    # Retorna apenas um registro
    # Returns a single record
    def fetchone(self):
        return self.result[0] if self.result else None


# ======================================================
# 5. FAKE CONN
# Simula conexão de banco de dados com métodos
# commit e rollback para manter padrão SQL.
#
# FAKE CONNECTION
# Simulates a database connection with
# commit and rollback methods.
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
# Carrega dados da planilha para o estado da sessão.
#
# INITIAL DATA LOAD
# Loads spreadsheet data into session state.
# ======================================================

if "df" not in st.session_state:
    st.session_state.df = carregar_dados()

df = st.session_state.df

# -----------------------------
# 2. ESTADOS E CONFIGURAÇÃO
# Controla estados da aplicação como navegação,
# edição de eventos e mensagens ao usuário.
#
# APP STATE AND CONFIGURATION
# Controls application state and navigation.
# -----------------------------

st.set_page_config(page_title="Agenda PRCOSET", page_icon="📅", layout="wide")
