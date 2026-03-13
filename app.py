import streamlit as st
import gspread
import pandas as pd
import time
from google.oauth2.service_account import Credentials
from datetime import date, time as dtime, datetime, timedelta, timezone

# ======================================================
# 1. CONEXÃO COM GOOGLE SHEETS
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

    # retry automático
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
# ======================================================

sheet = connect_sheets()


# ======================================================
# 4. FAKE CURSOR
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
# ======================================================

if "df" not in st.session_state:
    st.session_state.df = carregar_dados()

df = st.session_state.df


# -----------------------------
# 2. ESTADOS E CONFIGURAÇÃO
# -----------------------------
st.set_page_config(page_title="Agenda PRCOSET", page_icon="📅", layout="wide")

for key in ["aba_atual", "editando", "evento_id", "msg"]:
    if key not in st.session_state:
        st.session_state[key] = "LISTA" if key == "aba_atual" else None

# Título principal
st.title("📅 Agenda PRCOSET")

# Subtítulo / assinatura estilo jornal
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

# Menu Superior
cm1, cm2, _ = st.columns([1, 1, 4])

if cm1.button("📋 Ver Lista", use_container_width=True):
    st.session_state.aba_atual = "LISTA"
    st.rerun()

if cm2.button("➕ Novo Evento", use_container_width=True):
    st.session_state.aba_atual = "FORM"
    st.session_state.editando = False
    st.session_state.evento_id = None
    st.rerun()

# Mensagens
if st.session_state.msg:
    st.success(st.session_state.msg)
    st.session_state.msg = None


# -----------------------------
# 3. TELA DE FORMULÁRIO
# -----------------------------
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

        c_t1, c_t2 = st.columns(2)
        pres_val = c_t1.checkbox(
            "👑 Agenda Presidente?",
            value=bool(ev_db["agenda_presidente"]) if ev_db else False
        )
        mot_val = c_t2.checkbox(
            "🚗 Precisa Motorista?",
            value=bool(ev_db["precisa_motorista"]) if ev_db else False
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
            value=ev_db["hora_inicio"] if ev_db else time(9, 0)
        )
        hf_val = c[2].time_input(
            "⏰ Fim",
            value=ev_db["hora_fim"] if ev_db else time(10, 0)
        )

        loc_val = st.text_input(
            "📍 Local",
            value=ev_db["local"] if ev_db else ""
        )
        end_val = st.text_input(
            "🏠 Endereço",
            value=ev_db["endereco"] if ev_db else ""
        )

        cob_opcoes = ["Redes", "Foto", "Vídeo", "Imprensa"]
        cob_def = (
            ev_db["cobertura"].split(", ")
            if ev_db and ev_db["cobertura"]
            else []
        )

        cob_val = st.multiselect(
            "🎥 Cobertura",
            cob_opcoes,
            default=[c for c in cob_def if c in cob_opcoes]
        )

        resp_val = st.text_input(
            "👥 Responsáveis",
            value=ev_db["responsaveis"] if ev_db else ""
        )
        eq_val = st.text_input(
            "🎒 Equipamentos",
            value=ev_db["equipamentos"] if ev_db else ""
        )
        obs_val = st.text_area(
            "📝 Observações",
            value=ev_db["observacoes"] if ev_db else ""
        )

        cmot1, cmot2 = st.columns(2)
        nm_val = cmot1.text_input(
            "Nome Motorista",
            value=ev_db["motorista_nome"] if ev_db else ""
        )
        tm_val = cmot2.text_input(
            "Tel Motorista",
            value=ev_db["motorista_telefone"] if ev_db else ""
        )

        st_val = st.selectbox(
            "Status",
            ["ATIVO", "CANCELADO"],
            index=0 if not ev_db or ev_db["status"] == "ATIVO" else 1
        )

        salvar = st.form_submit_button(
            "💾 SALVAR EVENTO",
            use_container_width=True
        )

        if salvar:
            dados = (
                1 if pres_val else 0,
                tit_val,
                data_val,
                hi_val,
                hf_val,
                loc_val,
                end_val,
                ", ".join(cob_val),
                resp_val,
                eq_val,
                obs_val,
                1 if mot_val else 0,
                nm_val,
                tm_val,
                st_val,
            )

            try:
                if st.session_state.editando:
                    cursor.execute(
                        """
                        UPDATE eventos SET
                            agenda_presidente=%s,
                            titulo=%s,
                            data=%s,
                            hora_inicio=%s,
                            hora_fim=%s,
                            local=%s,
                            endereco=%s,
                            cobertura=%s,
                            responsaveis=%s,
                            equipamentos=%s,
                            observacoes=%s,
                            precisa_motorista=%s,
                            motorista_nome=%s,
                            motorista_telefone=%s,
                            status=%s
                        WHERE id=%s
                        """,
                        dados + (st.session_state.evento_id,),
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO eventos (
                            agenda_presidente, titulo, data, hora_inicio,
                            hora_fim, local, endereco, cobertura,
                            responsaveis, equipamentos, observacoes,
                            precisa_motorista, motorista_nome,
                            motorista_telefone, status
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        dados,
                    )

                conn.commit()
                st.session_state.aba_atual = "LISTA"
                st.session_state.msg = "💾 Evento salvo com sucesso!"
                st.rerun()

            except Exception as e:
                conn.rollback()
                st.error(f"Erro ao salvar: {e}")


# -----------------------------
# 4. TELA DE LISTAGEM
# -----------------------------
elif st.session_state.aba_atual == "LISTA":

    with st.expander("🔍 FILTRAR BUSCA", expanded=False):
        f_col1, f_col2, f_col3 = st.columns(3)

        with f_col1:
            filtro_data = st.date_input("Filtrar por Data", value=None)

        with f_col2:
            filtro_tipo = st.selectbox(
                "Tipo de Agenda",
                ["Todas", "Agenda do Presidente", "Outras Agendas"],
            )

        with f_col3:
            filtro_equipe = st.text_input(
                "Buscar por Responsável",
                placeholder="Ex: Fred, Ana...",
            )

    cursor.execute(
        "SELECT * FROM eventos ORDER BY data ASC, hora_inicio ASC"
    )
    eventos = cursor.fetchall()

    agora_dt = datetime.now(timezone(timedelta(hours=-3))).replace(
        tzinfo=None
    )
    hoje = agora_dt.date()
    hora_agora_str = agora_dt.time().strftime("%H:%M")

    def formatar_hora(valor):
        if isinstance(valor, time):
            return valor.strftime("%H:%M")
        try:
            return str(valor)[:5]
        except Exception:
            return "00:00"

    if not eventos:
        st.info("Nenhum evento encontrado.")

    for ev in eventos:
        d_dt = (
            ev["data"]
            if isinstance(ev["data"], date)
            else datetime.strptime(str(ev["data"]), "%Y-%m-%d").date()
        )

        if filtro_data and d_dt != filtro_data:
            continue
        if filtro_tipo == "Agenda do Presidente" and ev["agenda_presidente"] != 1:
            continue
        if filtro_tipo == "Outras Agendas" and ev["agenda_presidente"] == 1:
            continue
        if filtro_equipe and filtro_equipe.lower() not in str(ev["responsaveis"]).lower():
            continue

        cor_base = "#2b488e" if ev["agenda_presidente"] == 1 else "#109439"
        cor_fonte = "white"
        borda_4_lados = "1px solid rgba(255,255,255,0.2)"
        barra_esquerda = "12px solid #ffffff44"
        badge, opac = "", "1"
        decor = "line-through" if ev["status"] == "CANCELADO" else "none"

        if d_dt < hoje:
            cor_base, cor_fonte, opac = "#d9d9d9", "#666666", "0.7"
            barra_esquerda = "12px solid #999999"

        elif d_dt == hoje:
            borda_4_lados = "4px solid #FFD700"
            barra_esquerda = "12px solid #FFD700"
            badge = "<span style='background:#FFD700; color:black; padding:3px 10px; border-radius:10px; font-weight:bold; font-size:12px; margin-left:10px;'>HOJE!</span>"

            hi_s = formatar_hora(ev["hora_inicio"])
            hf_s = formatar_hora(ev["hora_fim"])
            if hi_s <= hora_agora_str <= hf_s:
                borda_4_lados = "4px solid #ff2b2b"
                barra_esquerda = "12px solid #ff2b2b"
                badge = "<span style='background:#ff2b2b; color:white; padding:3px 10px; border-radius:10px; font-weight:bold; font-size:12px; margin-left:10px;'>AGORA!</span>"

        link_zap = ""
        if ev["precisa_motorista"] == 1 and ev["motorista_telefone"]:
            zap_limpo = "".join(
                filter(str.isdigit, str(ev["motorista_telefone"]))
            )
            link_zap = f"<br>🚗 <b>Motorista:</b> {ev['motorista_nome']} (<a href='https://wa.me/{zap_limpo}' style='color:{cor_fonte}; font-weight:bold;'>{ev['motorista_telefone']}</a>)"

        st.markdown(
            f"""
        <div style="background:{cor_base}; color:{cor_fonte}; padding:22px; border-radius:15px; margin-bottom:15px; 
                    opacity:{opac}; text-decoration:{decor}; 
                    border:{borda_4_lados}; border-left:{barra_esquerda};">
            <h3 style="margin:0; font-size:22px;">{'👑' if ev['agenda_presidente'] == 1 else '📌'} {ev['titulo']} {badge} 
                <span style="float:right; font-size:12px; background:rgba(0,0,0,0.3); padding:5px 12px; border-radius:20px;">{ev['status']}</span>
            </h3>
            <div style="margin-top:12px; font-size:16px; line-height:1.6;">
                <b>📅 {d_dt.strftime('%d/%m/%Y')}</b> | ⏰ {formatar_hora(ev['hora_inicio'])} às {formatar_hora(ev['hora_fim'])}<br>
                📍 <b>Local:</b> {ev['local']}<br>
                🏠 <b>Endereço:</b> {ev['endereco']}<br>
                🎥 <b>Cobertura:</b> {ev['cobertura']} | 👥 <b>Equipe:</b> {ev['responsaveis']}<br>
                🎒 <b>Equipamentos:</b> {ev['equipamentos']} {link_zap}
            </div>
            <div style="background: rgba(255,255,255,0.15); padding: 12px; border-radius: 8px; margin-top: 15px; font-size:14px; border: 1px dashed rgba(255,255,255,0.3);">
                <b>📝 OBSERVAÇÕES:</b> {ev['observacoes'] if ev['observacoes'] else "Sem observações."}
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        c1, c2, c3, _ = st.columns([1, 1.2, 1, 4])

        if c1.button("✏️ Editar", key=f"e_{ev['id']}"):
            st.session_state.editando = True
            st.session_state.evento_id = ev["id"]
            st.session_state.aba_atual = "FORM"
            st.rerun()

        if c2.button("🚫 Alterar Status", key=f"s_{ev['id']}"):
            novo_s = "CANCELADO" if ev["status"] == "ATIVO" else "ATIVO"
            cursor.execute(
                "UPDATE eventos SET status=%s WHERE id=%s",
                (novo_s, ev["id"]),
            )
            conn.commit()
            st.rerun()

        if c3.button("🗑️ Excluir", key=f"d_{ev['id']}"):
            cursor.execute(
                "DELETE FROM eventos WHERE id=%s",
                (ev["id"],),
            )
            conn.commit()
            st.rerun()
