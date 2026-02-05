import streamlit as st
import requests
import pandas as pd
import io
from PIL import Image
import base64

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Stellantis Scanner", page_icon="🏭", layout="wide")

# ESTILO VISUAL: AZUL STELLANTIS (#243882)
st.markdown("""
<style>
    .stApp { background-color: #243882; color: #ffffff; }
    h1, h2, h3, p, span, label, div[data-testid="stMarkdownContainer"] p { color: #ffffff !important; }
    div.stButton > button { background-color: #ffffff; color: #243882; border: none; padding: 0.5rem 1rem; border-radius: 5px; font-weight: bold; width: 100%; }
    div.stButton > button:hover { background-color: #e0e0e0; color: #243882; }
    div[role="radiogroup"] label { background-color: rgba(255, 255, 255, 0.1); padding: 10px; border-radius: 5px; margin-right: 10px; border: 1px solid rgba(255,255,255,0.2); }
</style>
""", unsafe_allow_html=True)

# --- CABEÇALHO ---
col1, col2 = st.columns([1, 6])
with col1:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/b/b5/Stellantis.svg/2560px-Stellantis.svg.png", width=120)
with col2:
    st.title("Digitalizador de Apontamento - SPW")
    st.markdown("**Automacao via Conexão Direta (Sem SDK)**")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuração")
    api_key = st.text_input("Cole sua Gemini API Key:", type="password")

if not api_key:
    st.warning("👈 Insira sua API Key para começar.")
    st.stop()

# --- SELETOR DE TURNO ---
st.divider()
turno = st.radio(
    "1. Selecione o Turno Atual:",
    ["1º Turno (06:00 - 15:48)", "2º Turno (15:48 - 25:09)", "3º Turno (01:09 - 06:00)"],
    horizontal=True,
    index=1
)

# --- UPLOAD ---
st.markdown("### 2. Digitalizar Ficha")
uploaded_file = st.file_uploader("Tire uma foto ou carregue o arquivo", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Imagem Carregada", use_container_width=True)
    
    if st.button("🚀 Processar Apontamento"):
        with st.spinner("Conectando diretamente com o Gemini..."):
            try:
                # PREPARAR IMAGEM EM BASE64 (Necessário para envio direto)
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='JPEG')
                img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode("utf-8")

                # --- CHAMADA DIRETA À API (SEM BIBLIOTECA) ---
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                
                payload = {
                    "contents": [{
                        "parts": [
                            {"text": """
                                Atue como OCR industrial. Analise esta imagem.
                                Retorne APENAS um JSON (array de objetos) com:
                                "Data", "Maquina", "Hora", "Desenho", "Qtd_OK", "Qtd_NOK", "Cod_Parada".
                                Repita Data e Maquina do cabeçalho em todas as linhas.
                                Se hora tiver ':', mantenha.
                            """},
                            {"inline_data": {
                                "mime_type": "image/jpeg",
                                "data": img_base64
                            }}
                        ]
                    }]
                }
                
                # ENVIA O PEDIDO (POST)
                response = requests.post(url, json=payload)
                
                # VERIFICA SE DEU CERTO
                if response.status_code != 200:
                    st.error(f"Erro na API: {response.text}")
                    st.stop()
                
                # PROCESSA O RESULTADO
                result_json = response.json()
                try:
                    texto_resposta = result_json['candidates'][0]['content']['parts'][0]['text']
                    clean_json = texto_resposta.replace("```json", "").replace("```", "").strip()
                    df = pd.read_json(io.StringIO(clean_json))
                except:
                    st.error("A IA respondeu, mas não gerou uma tabela válida. Tente outra foto.")
                    st.stop()

                # --- REGRAS DE NEGÓCIO (PYTHON) ---
                def tratar_hora(hora_str):
                    if not hora_str: return ""
                    h_limpa = str(hora_str).replace(":", "").strip()
                    try:
                        h_num = int(h_limpa)
                    except:
                        return h_limpa 
                    
                    if "2º Turno" in turno:
                        if 0 <= h_num <= 200: # Regra da Madrugada
                            return str(h_num + 2400)
                    return str(h_num)

                if "Hora" in df.columns:
                    df["Hora"] = df["Hora"].apply(tratar_hora)
                
                # EXIBIÇÃO
                st.success("✅ Leitura concluída via Direct API!")
                df_editado = st.data_editor(df, num_rows="dynamic", use_container_width=True)
                
                tsv = df_editado.to_csv(sep="\t", index=False)
                st.code(tsv, language="text")
                st.info("👆 Copie e cole no Excel.")
                
            except Exception as e:
                st.error(f"Erro inesperado: {e}")