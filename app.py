import streamlit as st
import psycopg2
import psycopg2.extras
from datetime import datetime, date, time, timezone, timedelta

# -----------------------------
# 1. CONEXÃO E LIMPEZA
# -----------------------------
@st.cache_resource
def init_connection():
    return psycopg2.connect(
        host=st.secrets["DB_HOST"],       # Acessando a variável DB_HOST
        database=st.secrets["DB_NAME"],   # Acessando o nome do banco DB_NAME
        user=st.secrets["DB_USER"],       # Acessando o nome de usuário DB_USER
        password=st.secrets["DB_PASSWORD"],  # Acessando a senha DB_PASSWORD
        port=st.secrets["DB_PORT"],       # Acessando a porta DB_PORT
        sslmode=st.secrets["DB_SSLMODE"]  # Acessando o SSL
    )

conn = init_connection()
# Cursor que retorna dicionário em vez de tupla
cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
conn.rollback()

# -----------------------------
# 2. ESTADOS E CONFIGURAÇÃO
# -----------------------------
st.set_page_config(page_title="Agenda Portfolio", page_icon="📅", layout="wide")

for key in ["aba_atual", "editando", "evento_id", "msg"]:
    if key not in st.session_state:
        st.session_state[key] = "LISTA" if key == "aba_atual" else None

st.title("📅 Agenda Portfolio")

# Menu Superior
cm1, cm2, _ = st.columns([1, 1, 4])
if cm1.button("📋 Ver Lista", use_container_width=True):
    st.session_state.aba_atual = "LISTA"
    st.rerun()
if cm2.button("➕ Novo Evento", use_container_width=True):
    st.session_state.aba_atual = "FORM"
    st.session_state.editando, st.session_state.evento_id = False, None
    st.rerun()

st.markdown("---")

if st.session_state.msg:
    st.success(st.session_state.msg)
    st.session_state.msg = None

# -----------------------------
# 3. TELA DE FORMULÁRIO
# -----------------------------
if st.session_state.aba_atual == "FORM":
    ev_db = None
    if st.session_state.editando and st.session_state.evento_id:
        cursor.execute("SELECT * FROM eventos WHERE id=%s", (st.session_state.evento_id,))
        ev_db = cursor.fetchone()

    with st.form("form_evento"):
        st.subheader("📝 Detalhes do Evento")
        
        c_t1, c_t2 = st.columns(2)
        pres_val = c_t1.checkbox("👑 Agenda Presidente?", value=bool(ev_db["agenda_presidente"]) if ev_db else False)
        mot_val = c_t2.checkbox("🚗 Precisa Motorista?", value=bool(ev_db["precisa_motorista"]) if ev_db else False)
        
        tit_val = st.text_input("📝 Título", value=ev_db["titulo"] if ev_db else "")
        
        c = st.columns(3)
        data_val = c[0].date_input("📅 Data", value=ev_db["data"] if ev_db else date.today())
        hi_val = c[1].time_input("⏰ Início", value=ev_db["hora_inicio"] if ev_db else time(9,0))
        hf_val = c[2].time_input("⏰ Fim", value=ev_db["hora_fim"] if ev_db else time(10,0))

        loc_val = st.text_input("📍 Local", value=ev_db["local"] if ev_db else "")
        end_val = st.text_input("🏠 Endereço", value=ev_db["endereco"] if ev_db else "")
        
        cob_opcoes = ["Redes", "Foto", "Vídeo", "Imprensa"]
        cob_def = ev_db["cobertura"].split(", ") if ev_db and ev_db["cobertura"] else []
        cob_val = st.multiselect("🎥 Cobertura", cob_opcoes, default=[c for c in cob_def if c in cob_opcoes])
        
        resp_val = st.text_input("👥 Responsáveis", value=ev_db["responsaveis"] if ev_db else "")
        eq_val = st.text_input("🎒 Equipamentos", value=ev_db["equipamentos"] if ev_db else "")
        obs_val = st.text_area("📝 Observações", value=ev_db["observacoes"] if ev_db else "")
        
        cmot1, cmot2 = st.columns(2)
        nm_val = cmot1.text_input("Nome Motorista", value=ev_db["motorista_nome"] if ev_db else "")
        tm_val = cmot2.text_input("Tel Motorista", value=ev_db["motorista_telefone"] if ev_db else "")
        
        st_val = st.selectbox("Status", ["ATIVO", "CANCELADO"], index=0 if not ev_db or ev_db["status"]=="ATIVO" else 1)

        salvar = st.form_submit_button("💾 SALVAR EVENTO", use_container_width=True)

        if salvar:
            dados = (
                1 if pres_val else 0, tit_val, data_val, hi_val, hf_val,
                loc_val, end_val, ", ".join(cob_val), resp_val, eq_val,
                obs_val, 1 if mot_val else 0, nm_val, tm_val, st_val
            )
            try:
                if st.session_state.editando:
                    cursor.execute("""UPDATE eventos SET agenda_presidente=%s, titulo=%s, data=%s, hora_inicio=%s, hora_fim=%s, 
                        local=%s, endereco=%s, cobertura=%s, responsaveis=%s, equipamentos=%s, observacoes=%s, 
                        precisa_motorista=%s, motorista_nome=%s, motorista_telefone=%s, status=%s WHERE id=%s""", 
                        dados + (st.session_state.evento_id,))
                else:
                    cursor.execute("""INSERT INTO eventos (agenda_presidente, titulo, data, hora_inicio, hora_fim, local, endereco, 
                        cobertura, responsaveis, equipamentos, observacoes, precisa_motorista, motorista_nome, motorista_telefone, status) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", dados)
                conn.commit()
                st.session_state.aba_atual, st.session_state.msg = "LISTA", "💾 Evento salvo com sucesso!"
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
        with f_col1: filtro_data = st.date_input("Filtrar por Data", value=None)
        with f_col2: filtro_tipo = st.selectbox("Tipo de Agenda", ["Todas", "Agenda do Presidente", "Outras Agendas"])
        with f_col3: filtro_equipe = st.text_input("Buscar por Responsável", placeholder="Ex: Fred, Ana...")

    cursor.execute("SELECT * FROM eventos ORDER BY data ASC, hora_inicio ASC")
    eventos = cursor.fetchall()

    if not eventos:
        st.info("Nenhum evento encontrado.")

    for ev in eventos:
        d_dt = ev["data"] if isinstance(ev["data"], date) else datetime.strptime(str(ev["data"]), "%Y-%m-%d").date()

        if filtro_data and d_dt != filtro_data: continue
        if filtro
