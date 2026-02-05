import streamlit as st
import requests
import pandas as pd
import io
from PIL import Image
import base64

st.set_page_config(page_title="Diagnóstico Stellantis", page_icon="🚑", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #243882; color: white; }
    h1, h2, h3, p { color: white !important; }
    .stTextInput input { color: #333333; }
</style>
""", unsafe_allow_html=True)

st.title("🚑 Modo de Diagnóstico de Erros")
st.markdown("Vamos descobrir exatamente por que o Google está bloqueando sua chave.")

api_key = st.text_input("Cole sua Chave API (Gemini) aqui:", type="password")

if st.button("🔍 TESTAR CONEXÃO AGORA"):
    if not api_key:
        st.warning("Cole a chave primeiro.")
    else:
        st.info("Tentando conectar com o servidor do Google...")
        
        # Tenta listar os modelos disponíveis (Isso é o teste mais básico possível)
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key.strip()}"
        
        try:
            response = requests.get(url)
            
            st.write("---")
            st.write(f"**Código de Status:** {response.status_code}")
            
            if response.status_code == 200:
                st.success("✅ A CONEXÃO FUNCIONOU! Sua chave está ativa.")
                st.write("Modelos disponíveis para você:")
                dados = response.json()
                # Mostra a lista de modelos que o Google permite você usar
                modelos = [m['name'] for m in dados.get('models', [])]
                st.json(modelos)
                st.balloons()
            else:
                st.error("❌ O GOOGLE RECUSOU A CONEXÃO.")
                st.write("Aqui está o motivo exato (Erro cru):")
                # ISSO AQUI VAI NOS DIZER O PROBLEMA REAL 👇
                st.json(response.json()) 
                
        except Exception as e:
            st.error(f"Erro grave de conexão: {e}")