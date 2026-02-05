import streamlit as st
import requests
import pandas as pd
import io
from PIL import Image
import base64

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Stellantis Scanner", page_icon="🏭", layout="wide")

# --- ESTILO VISUAL INDUSTRIAL (Amarelo e Azul) ---
st.markdown("""
<style>
    .stApp { background-color: #243882; color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #00133b; border-right: 1px solid rgba(255, 255, 255, 0.1); }
    h1, h2, h3, p, span, label, div[data-testid="stMarkdownContainer"] p, [data-testid="stSidebar"] label { color: #ffffff !important; }
    
    /* Botões Amarelos de Alto Contraste */
    div.stButton > button, [data-testid="stFileUploader"] button {
        background-color: #FFC107 !important; color: #000000 !important; border: none !important;
        padding: 0.6rem 1rem; border-radius: 6px; font-weight: 800 !important; text-transform: uppercase;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    div.stButton > button:hover { background-color: #FFD700 !important; transform: translateY(-2px); }
    
    /* Inputs e Seletores */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] { color: #333333; background-color: #ffffff; }
    div[role="radiogroup"] label { background-color: rgba(0, 19, 59, 0.6); padding: 12px; border-radius: 8px; border: 2px solid rgba(255, 255, 255, 0.2); }
</style>
""", unsafe_allow_html=True)

# --- CABEÇALHO ---
col1, col2 = st.columns([1, 6])
with col1:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/b/b5/Stellantis.svg/2560px-Stellantis.svg.png", width=120)
with col2:
    st.title("Digitalizador de Apontamento - SPW")
    st.markdown("**Sistema Multi-Modelo (Seletor de IA)**")

# --- SIDEBAR: CONFIGURAÇÕES ---
with st.sidebar:
    st.header("⚙️ Configuração")
    api_key_input = st.text_input("Cole sua Gemini API Key:", type="password")
    api_key = api_key_input.strip() if api_key_input else ""
    
    st.markdown("---")
    st.markdown("### 📡 Sintonizar Modelo")
    st.info("Se der erro 404, troque o modelo abaixo:")
    
    # O PULO DO GATO: SELETOR DE MODELOS
    modelo_escolhido = st.selectbox(
        "Qual versão da IA usar?",
        options=[
            "gemini-1.5-flash",       # Padrão
            "gemini-1.5-flash-001",   # Versão específica (Mais estável)
            "gemini-1.5-flash-8b",    # Versão leve (Nova)
            "gemini-1.5-pro",         # Versão potente
            "gemini-2.0-flash-exp"    # Experimental
        ],
        index=0
    )

if not api_key:
    st.warning("👈 Insira sua API Key na barra lateral para começar.")
    st.stop()

# --- TURNO ---
st.divider()
turno = st.radio(
    "1. Selecione o Turno:",
    ["1º Turno (06:00 - 15:48)", "2º Turno (15:48 - 25:09)", "3º Turno (01:09 - 06:00)"],
    horizontal=True, index=1
)

# --- UPLOAD ---
st.markdown("### 2. Digitalizar Ficha")
uploaded_file = st.file_uploader("Carregue a imagem:", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption=f"Imagem Carregada | Usando: {modelo_escolhido}", use_container_width=True)
    
    if st.button("🚀 PROCESSAR APONTAMENTO AGORA"):
        with st.spinner(f"Conectando com {modelo_escolhido}..."):
            try:
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='JPEG')
                img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode("utf-8")

                # URL DINÂMICA BASEADA NA ESCOLHA DA BARRA LATERAL
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo_escolhido}:generateContent?key={api_key}"
                
                payload = {
                    "contents": [{
                        "parts": [
                            {"text": """Atue como OCR industrial. Retorne JSON array com: "Data", "Maquina", "Hora", "Desenho", "Qtd_OK", "Qtd_NOK", "Cod_Parada". Repita Data e Maquina do topo em todas as linhas."""},
                            {"inline_data": {"mime_type": "image/jpeg", "data": img_base64}}
                        ]
                    }]
                }
                
                response = requests.post(url, json=payload)
                
                if response.status_code != 200:
                    st.error(f"Erro {response.status_code} no modelo {modelo_escolhido}:")
                    st.code(response.text)
                    st.warning("👈 Tente selecionar OUTRO MODELO na barra lateral e clique no botão de novo.")
                    st.stop()
                
                result_json = response.json()
                try:
                    texto = result_json['candidates'][0]['content']['parts'][0]['text']
                    clean_json = texto.replace("```json", "").replace("```", "").strip()
                    df = pd.read_json(io.StringIO(clean_json))
                except:
                    st.error("A IA respondeu mas não gerou tabela. Tente outra foto.")
                    st.stop()

                # REGRAS DE NEGÓCIO
                def tratar_hora(h):
                    h = str(h).replace(":", "").strip()
                    try: h_num = int(h)
                    except: return h
                    if "2º Turno" in turno and 0 <= h_num <= 200: return str(h_num + 2400)
                    return str(h_num)

                if "Hora" in df.columns: df["Hora"] = df["Hora"].apply(tratar_hora)
                
                st.success("✅ Sucesso!")
                df_editado = st.data_editor(df, num_rows="dynamic", use_container_width=True)
                st.code(df_editado.to_csv(sep="\t", index=False), language="text")
                st.info("👆 Copie acima e cole no Excel.")
                
            except Exception as e:
                st.error(f"Erro: {e}")