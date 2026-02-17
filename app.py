import streamlit as st
import psycopg2
import psycopg2.extras

# ======================================================
# 1. CONEXÃO COM O BANCO DE DADOS
# ======================================================

@st.cache_resource
def init_connection():
    """
    Inicializa a conexão com o PostgreSQL (Supabase).
    Usa pooler IPv4 e trata erros corretamente.
    """
    try:
        conn = psycopg2.connect(
            st.secrets["DATABASE_URL"],
            sslmode="require",
            connect_timeout=10,
            application_name="streamlit_app"
        )
        return conn

    except Exception as e:
        st.error("❌ Erro ao conectar ao banco de dados.")
        st.exception(e)
        return None


# ======================================================
# 2. INICIALIZA CONEXÃO
# ======================================================

conn = init_connection()

if conn is None:
    st.stop()

# ======================================================
# 3. CURSOR
# ======================================================

try:
    cursor = conn.cursor(
        cursor_factory=psycopg2.extras.RealDictCursor
    )

    # Garante que não haja transações pendentes
    conn.rollback()

except Exception as e:
    st.error("❌ Erro ao criar cursor.")
    st.exception(e)
    st.stop()

# ======================================================
# 4. TESTE DE CONEXÃO (opcional, mas recomendado)
# ======================================================

try:
    cursor.execute("SELECT 1 as teste;")
    result = cursor.fetchone()
    st.success("✅ Conexão com Supabase OK!")

except Exception as e:
    st.error("❌ Conectou mas não conseguiu executar query.")
    st.exception(e)



# ======================================================
# 2. CONFIGURAÇÃO DA APLICAÇÃO E ESTADO
# ======================================================

st.set_page_config(
    page_title="Agenda PRCOSET",
    page_icon="📅",
    layout="wide"
)

# Estados globais da aplicação
DEFAULT_STATES = {
    "aba_atual": "LISTA",
    "editando": None,
    "evento_id": None,
    "msg": None
}

for key, value in DEFAULT_STATES.items():
    if key not in st.session_state:
        st.session_state[key] = value

st.title("📅 Agenda PRCOSET")


# ======================================================
# 3. MENU SUPERIOR
# ======================================================

col_menu_1, col_menu_2, _ = st.columns([1, 1, 4])

if col_menu_1.button("📋 Ver Lista", use_container_width=True):
    st.session_state.aba_atual = "LISTA"
    st.rerun()

if col_menu_2.button("➕ Novo Evento", use_container_width=True):
    st.session_state.aba_atual = "FORM"
    st.session_state.editando = False
    st.session_state.evento_id = None
    st.rerun()

st.markdown("---")

# Mensagem de feedback ao usuário
if st.session_state.msg:
    st.success(st.session_state.msg)
    st.session_state.msg = None


# ======================================================
# 4. FORMULÁRIO DE EVENTOS (CRIAR / EDITAR)
# ======================================================

if st.session_state.aba_atual == "FORM":

    evento_db = None

    # Carrega evento do banco se estiver editando
    if st.session_state.editando and st.session_state.evento_id:
        cursor.execute(
            "SELECT * FROM eventos WHERE id = %s",
            (st.session_state.evento_id,)
        )
        evento_db = cursor.fetchone()

    with st.form("form_evento"):
        st.subheader("📝 Detalhes do Evento")

        col_flag_1, col_flag_2 = st.columns(2)
        agenda_presidente = col_flag_1.checkbox(
            "👑 Agenda Presidente?",
            value=bool(evento_db["agenda_presidente"]) if evento_db else False
        )
        precisa_motorista = col_flag_2.checkbox(
            "🚗 Precisa Motorista?",
            value=bool(evento_db["precisa_motorista"]) if evento_db else False
        )

        titulo = st.text_input(
            "📝 Título",
            value=evento_db["titulo"] if evento_db else ""
        )

        col_data = st.columns(3)
        data_evento = col_data[0].date_input(
            "📅 Data",
            value=evento_db["data"] if evento_db else date.today()
        )
        hora_inicio = col_data[1].time_input(
            "⏰ Início",
            value=evento_db["hora_inicio"] if evento_db else time(9, 0)
        )
        hora_fim = col_data[2].time_input(
            "⏰ Fim",
            value=evento_db["hora_fim"] if evento_db else time(10, 0)
        )

        local = st.text_input(
            "📍 Local",
            value=evento_db["local"] if evento_db else ""
        )
        endereco = st.text_input(
            "🏠 Endereço",
            value=evento_db["endereco"] if evento_db else ""
        )

        opcoes_cobertura = ["Redes", "Foto", "Vídeo", "Imprensa"]
        cobertura_padrao = (
            evento_db["cobertura"].split(", ")
            if evento_db and evento_db["cobertura"]
            else []
        )

        cobertura = st.multiselect(
            "🎥 Cobertura",
            opcoes_cobertura,
            default=[c for c in cobertura_padrao if c in opcoes_cobertura]
        )

        responsaveis = st.text_input(
            "👥 Responsáveis",
            value=evento_db["responsaveis"] if evento_db else ""
        )
        equipamentos = st.text_input(
            "🎒 Equipamentos",
            value=evento_db["equipamentos"] if evento_db else ""
        )
        observacoes = st.text_area(
            "📝 Observações",
            value=evento_db["observacoes"] if evento_db else ""
        )

        col_motorista_1, col_motorista_2 = st.columns(2)
        motorista_nome = col_motorista_1.text_input(
            "Nome Motorista",
            value=evento_db["motorista_nome"] if evento_db else ""
        )
        motorista_telefone = col_motorista_2.text_input(
            "Tel Motorista",
            value=evento_db["motorista_telefone"] if evento_db else ""
        )

        status = st.selectbox(
            "Status",
            ["ATIVO", "CANCELADO"],
            index=0 if not evento_db or evento_db["status"] == "ATIVO" else 1
        )

        salvar = st.form_submit_button(
            "💾 SALVAR EVENTO",
            use_container_width=True
        )

        if salvar:
            dados_evento = (
                1 if agenda_presidente else 0,
                titulo,
                data_evento,
                hora_inicio,
                hora_fim,
                local,
                endereco,
                ", ".join(cobertura),
                responsaveis,
                equipamentos,
                observacoes,
                1 if precisa_motorista else 0,
                motorista_nome,
                motorista_telefone,
                status
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
                        dados_evento + (st.session_state.evento_id,)
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
                        dados_evento
                    )

                conn.commit()
                st.session_state.aba_atual = "LISTA"
                st.session_state.msg = "💾 Evento salvo com sucesso!"
                st.rerun()

            except Exception as erro:
                conn.rollback()
                st.error(f"Erro ao salvar: {erro}")


# ======================================================
# 5. LISTAGEM DE EVENTOS
# ======================================================

elif st.session_state.aba_atual == "LISTA":

    with st.expander("🔍 FILTRAR BUSCA", expanded=False):
        col_filtro_1, col_filtro_2, col_filtro_3 = st.columns(3)

        filtro_data = col_filtro_1.date_input(
            "Filtrar por Data",
            value=None
        )
        filtro_tipo = col_filtro_2.selectbox(
            "Tipo de Agenda",
            ["Todas", "Agenda do Presidente", "Outras Agendas"]
        )
        filtro_responsavel = col_filtro_3.text_input(
            "Buscar por Responsável",
            placeholder="Ex: Fred, Ana..."
        )

    cursor.execute(
        "SELECT * FROM eventos ORDER BY data ASC, hora_inicio ASC"
    )
    eventos = cursor.fetchall()

    agora = datetime.now(
        timezone(timedelta(hours=-3))
    ).replace(tzinfo=None)

    hoje = agora.date()
    hora_atual = agora.time().strftime("%H:%M")

    def formatar_hora(valor):
        """Formata horários vindos do banco."""
        if isinstance(valor, time):
            return valor.strftime("%H:%M")
        try:
            return str(valor)[:5]
        except Exception:
            return "00:00"

    if not eventos:
        st.info("Nenhum evento encontrado.")

    for evento in eventos:

        data_evento = (
            evento["data"]
            if isinstance(evento["data"], date)
            else datetime.strptime(
                str(evento["data"]),
                "%Y-%m-%d"
            ).date()
        )

        # Aplicação dos filtros
        if filtro_data and data_evento != filtro_data:
            continue
        if filtro_tipo == "Agenda do Presidente" and evento["agenda_presidente"] != 1:
            continue
        if filtro_tipo == "Outras Agendas" and evento["agenda_presidente"] == 1:
            continue
        if filtro_responsavel and filtro_responsavel.lower() not in str(evento["responsaveis"]).lower():
            continue

        # Definição de cores e estilos
        cor_base = "#2b488e" if evento["agenda_presidente"] == 1 else "#109439"
        cor_fonte = "white"
        opacidade = "1"
        decoracao = "line-through" if evento["status"] == "CANCELADO" else "none"
        borda = "1px solid rgba(255,255,255,0.2)"
        barra_esquerda = "12px solid #ffffff44"
        badge = ""

        if data_evento < hoje:
            cor_base = "#d9d9d9"
            cor_fonte = "#666666"
            opacidade = "0.7"
            barra_esquerda = "12px solid #999999"

        elif data_evento == hoje:
            borda = "4px solid #FFD700"
            barra_esquerda = "12px solid #FFD700"
            badge = "<span style='background:#FFD700; color:black; padding:3px 10px; border-radius:10px; font-size:12px;'>HOJE!</span>"

            hi = formatar_hora(evento["hora_inicio"])
            hf = formatar_hora(evento["hora_fim"])

            if hi <= hora_atual <= hf:
                borda = "4px solid #ff2b2b"
                barra_esquerda = "12px solid #ff2b2b"
                badge = "<span style='background:#ff2b2b; color:white; padding:3px 10px; border-radius:10px; font-size:12px;'>AGORA!</span>"

        link_motorista = ""
        if evento["precisa_motorista"] == 1 and evento["motorista_telefone"]:
            telefone_limpo = "".join(filter(str.isdigit, str(evento["motorista_telefone"])))
            link_motorista = f"<br>🚗 <b>Motorista:</b> {evento['motorista_nome']} (<a href='https://wa.me/{telefone_limpo}' style='color:{cor_fonte}; font-weight:bold;'>{evento['motorista_telefone']}</a>)"

        st.markdown(f"""
        <div style="background:{cor_base}; color:{cor_fonte}; padding:22px; border-radius:15px;
                    margin-bottom:15px; opacity:{opacidade}; text-decoration:{decoracao};
                    border:{borda}; border-left:{barra_esquerda};">
            <h3>
                {'👑' if evento['agenda_presidente'] == 1 else '📌'} {evento['titulo']} {badge}
                <span style="float:right; font-size:12px;">{evento['status']}</span>
            </h3>
            <p>
                📅 {data_evento.strftime('%d/%m/%Y')} |
                ⏰ {formatar_hora(evento['hora_inicio'])} às {formatar_hora(evento['hora_fim'])}<br>
                📍 {evento['local']}<br>
                🏠 {evento['endereco']}<br>
                🎥 {evento['cobertura']} | 👥 {evento['responsaveis']}<br>
                🎒 {evento['equipamentos']} {link_motorista}
            </p>
        </div>
        """, unsafe_allow_html=True)

        col_btn_1, col_btn_2, col_btn_3, _ = st.columns([1, 1.2, 1, 4])

        if col_btn_1.button("✏️ Editar", key=f"edit_{evento['id']}"):
            st.session_state.editando = True
            st.session_state.evento_id = evento["id"]
            st.session_state.aba_atual = "FORM"
            st.rerun()

        if col_btn_2.button("🚫 Alterar Status", key=f"status_{evento['id']}"):
            novo_status = "CANCELADO" if evento["status"] == "ATIVO" else "ATIVO"
            cursor.execute(
                "UPDATE eventos SET status=%s WHERE id=%s",
                (novo_status, evento["id"])
            )
            conn.commit()
            st.rerun()

        if col_btn_3.button("🗑️ Excluir", key=f"delete_{evento['id']}"):
            cursor.execute(
                "DELETE FROM eventos WHERE id=%s",
                (evento["id"],)
            )
            conn.commit()
            st.rerun()


