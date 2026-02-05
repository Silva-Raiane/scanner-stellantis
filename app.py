import streamlit as st
import requests
import pandas as pd
import io
from PIL import Image
import base64
import time

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Stellantis Scanner", page_icon="🏭", layout="wide")

# --- ESTILO VISUAL INDUSTRIAL (MANTIDO) ---
st.markdown("""
<style>
    .stApp { background-color: #243882; color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #00133b; border-right: 1px solid rgba(255, 255, 255, 0.1); }
    h1, h2, h3, p, span, label, div[data-testid="stMarkdownContainer"] p, [data-testid="stSidebar"] label { color: #ffffff !important; }
    div.stButton > button, [data-testid="stFileUploader"] button {
        background-color: #FFC107 !important; color: #000000 !important; border: none !important;
        padding: 0.6rem 1rem; border-radius: 6px; font-weight: 800 !important; text-transform: uppercase;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    div.stButton > button:hover { background-color: #FFD700 !important; transform: translateY(-2px); }
    .stTextInput input { color: #333333; background-color: #ffffff; }
    div[role="radiogroup"] label { background-color: rgba(0, 19, 59, 0.6); padding: 12px; border-radius: 8px; border: 2px solid rgba(255, 255, 255, 0.2); }
</style>
""", unsafe_allow_html=True)

# --- CABEÇALHO ---
col1, col2 = st.columns([1, 6])
with col1:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/b/b5/Stellantis.svg/2560px-Stellantis.svg.png", width=120)
with col2:
    st.title("Digitalizador de Apontamento - SPW")
    st.markdown("**Sistema com Auto-Conexão (Tentativa Múltipla)**")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuração")
    api_key_input = st.text_input("Cole sua Gemini API Key:", type="password")
    api_key = api_key_input.strip() if api_key_input else ""

if not api_key:
    st.warning("👈 Insira sua API Key para começar.")
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
    st.image(image, caption="Imagem Carregada", use_container_width=True)
    
    if st.button("🚀 PROCESSAR APONTAMENTO AGORA"):
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG')
        img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode("utf-8")

        # --- A LISTA DE TENTATIVAS (O SEGREDO) ---
        # O código vai tentar conectar nesses endereços um por um até conseguir
        modelos_para_testar = [
            ("gemini-1.5-flash", "v1beta"),
            ("gemini-1.5-flash", "v1"),
            ("gemini-1.5-flash-latest", "v1beta"),
            ("gemini-1.5-flash-001", "v1beta"),
            ("gemini-1.5-pro", "v1beta"), # Se o flash falhar, tenta o Pro (mais lento mas funciona)
            ("gemini-2.0-flash-exp", "v1beta")
        ]

        sucesso = False
        resultado_final = None
        
        container_status = st.empty()

        for nome_modelo, versao_api in modelos_para_testar:
            try:
                container_status.info(f"🔄 Tentando conectar via canal: {nome_modelo} ({versao_api})...")
                
                url = f"https://generativelanguage.googleapis.com/{versao_api}/models/{nome_modelo}:generateContent?key={api_key}"
                
                payload = {
                    "contents": [{
                        "parts": [
                            {"text": """Atue como OCR industrial. Retorne APENAS um JSON array com chaves: "Data", "Maquina", "Hora", "Desenho", "Qtd_OK", "Qtd_NOK", "Cod_Parada". Repita Data e Maquina do cabeçalho em todas as linhas. Se a hora tiver ':', mantenha."""},
                            {"inline_data": {"mime_type": "image/jpeg", "data": img_base64}}
                        ]
                    }]
                }
                
                response = requests.post(url, json=payload, timeout=15)
                
                if response.status_code == 200:
                    resultado_final = response.json()
                    sucesso = True
                    container_status.success(f"✅ Conectado com sucesso usando {nome_modelo}!")
                    break # Para o loop pois funcionou
                else:
                    print(f"Falha no {nome_modelo}: {response.status_code}")
                    continue # Tenta o próximo da lista

            except Exception as e:
                continue

        # --- PROCESSAMENTO DO RESULTADO ---
        if sucesso and resultado_final:
            try:
                texto = resultado_final['candidates'][0]['content']['parts'][0]['text']
                clean_json = texto.replace("```json", "").replace("```", "").strip()
                df = pd.read_json(io.StringIO(clean_json))

                # REGRAS DE NEGÓCIO
                def tratar_hora(h):
                    h = str(h).replace(":", "").strip()
                    try: h_num = int(h)
                    except: return h
                    if "2º Turno" in turno and 0 <= h_num <= 200: return str(h_num + 2400)
                    return str(h_num)

                if "Hora" in df.columns: df["Hora"] = df["Hora"].apply(tratar_hora)
                
                st.markdown("### Resultado:")
                df_editado = st.data_editor(df, num_rows="dynamic", use_container_width=True)
                
                st.info("👇 Copie para o Excel abaixo:")
                st.code(df_editado.to_csv(sep="\t", index=False), language="text")
                
            except Exception as e:
                st.error("A IA conectou, mas não conseguiu ler a tabela. A foto pode estar desfocada.")
        else:
            st.error("❌ Não foi possível conectar com nenhum modelo gratuito.")
            st.error("Verifique se sua Chave API está correta e ativa no Google AI Studio.")
            st.markdown("[Criar nova chave aqui](https://aistudio.google.com/app/apikey)")