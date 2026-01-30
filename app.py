import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

st.title("Teste de conexão Supabase 🚀")

@st.cache_resource
def get_engine():
    return create_engine(
        st.secrets["DATABASE_URL"],
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=2,
    )

engine = get_engine()

try:
    with engine.connect() as conn:
        df = pd.read_sql(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'",
            conn
        )

    st.success("Conectado com sucesso ao Supabase!")
    st.write("Tabelas encontradas:")
    st.dataframe(df)

except Exception as e:
    st.error("Erro ao conectar no banco")
    st.exception(e)



