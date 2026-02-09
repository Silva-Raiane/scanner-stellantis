import streamlit as st
import requests
import pandas as pd
import io
from PIL import Image
import base64

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Stellantis Scanner",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)


st.markdown("""
<style>

/* FUNDO */
.stApp {
    background-color: #eef1f5;
    font-family: "Segoe UI", Arial, sans-serif;
}

/* SIDEBAR */
[data-testid="stSidebar"] {
    background-color: #0b1f3f;
    padding: 20px;
}

/* TEXTO SIDEBAR */
[data-testid="stSidebar"] * {
    color: #fffff !important;
}

/* INPUT SIDEBAR */
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] div[data-baseweb="select"] {
    background: white !important;
    color: black !important;
    border-radius: 6px;
}

/* TÍTULOS */
h1, h2, h3 {
    color: #0b1f3f !important;
    font-weight: 600;
}

/* TEXTO */
p, label, span {
    color: #333 !important;
}

/* BOTÕES */
div.stButton > button {
    background-color: #0b1f3f !important;
    color: white !important;
    border-radius: 6px;
    border: none;
    padding: 10px 18px;
    font-weight: 600;
}

div.stButton > button:hover {
    background-color: #163a73 !important;
}

/* INPUTS */
.stTextInput input,
.stFileUploader,
.stRadio {
    background: white !important;
    border-radius: 6px;
}

/* TABELAS */
[data-testid="stDataFrame"] {
    background: white;
}

/* LOGO */
.stImage img {
    display: block;
    margin-left: auto;
    margin-right: auto;
}

/* LINHA */
hr {
    border-top: 1px solid #dcdcdc;
}

</style>
""", unsafe_allow_html=True)


# --- CABEÇALHO ---
col1, col2 = st.columns([1, 6])
with col1:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/b/b5/Stellantis.svg/2560px-Stellantis.svg.png", width=120)
with col2:
    st.title("Digitalizador de Apontamento - SPW")
    st.markdown("**Seletor Dinâmico de Modelos**")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuração")
    api_key_input = st.text_input("Cole sua Gemini API Key:", type="password")
    api_key = api_key_input.strip() if api_key_input else ""
    
    modelos_disponiveis = []
    modelo_selecionado = ""

    if api_key:
        try:
            url_modelos = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
            resp = requests.get(url_modelos)
            if resp.status_code == 200:
                dados = resp.json()
                modelos_disponiveis = [
                    m['name'].replace('models/', '')
                    for m in dados.get('models', [])
                    if 'generateContent' in m['supportedGenerationMethods']
                    and 'gemini' in m['name']
                ]
                st.success(f"✅ {len(modelos_disponiveis)} modelos encontrados!")
            else:
                st.error("Erro ao buscar modelos.")
        except:
            pass

    if modelos_disponiveis:
        st.markdown("### 📡 Escolha o Modelo")
        index_padrao = 0
        if "gemini-2.0-flash-001" in modelos_disponiveis:
            index_padrao = modelos_disponiveis.index("gemini-2.0-flash-001")
        elif "gemini-flash-latest" in modelos_disponiveis:
            index_padrao = modelos_disponiveis.index("gemini-flash-latest")

        modelo_selecionado = st.selectbox(
            "Qual IA usar?",
            modelos_disponiveis,
            index=index_padrao
        )
    else:
        st.warning("Cole a chave para carregar a lista.")

if not api_key:
    st.stop()

# --- APP PRINCIPAL ---
st.divider()
col_turno, col_upload = st.columns([1, 2])

with col_turno:
    st.subheader("1. Turno")
    turno = st.radio(
        "Selecione:",
        ["1º Turno (06h-15h)", "2º Turno (15h-01h)", "3º Turno (01h-06h)"],
        index=1
    )

with col_upload:
    st.subheader("2. Foto")
    uploaded_file = st.file_uploader("Subir imagem", type=["jpg", "png", "jpeg"])

if uploaded_file and modelo_selecionado:
    image = Image.open(uploaded_file)
    st.image(image, caption=f"Usando modelo: {modelo_selecionado}", use_container_width=True)

    if st.button("🚀 PROCESSAR AGORA"):
        with st.spinner(f"Processando com {modelo_selecionado}..."):
            try:
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='JPEG')
                img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode("utf-8")

                url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo_selecionado}:generateContent?key={api_key}"

                payload = {
                    "contents": [{
                        "parts": [
                            {"text": """Atue como OCR industrial. Retorne JSON array: "Data", "Maquina", "Hora", "Desenho", "Qtd_OK", "Qtd_NOK", "Cod_Parada". Repita Data/Maquina do topo. Se hora tiver ':', mantenha."""},
                            {"inline_data": {"mime_type": "image/jpeg", "data": img_base64}}
                        ]
                    }]
                }

                response = requests.post(url, json=payload)

                if response.status_code != 200:
                    st.error(f"Erro {response.status_code}: {response.text}")
                    st.warning("👉 Tente selecionar OUTRO modelo.")
                    st.stop()

                result = response.json()
                texto = result['candidates'][0]['content']['parts'][0]['text']
                clean_json = texto.replace("```json", "").replace("```", "").strip()
                df = pd.read_json(io.StringIO(clean_json))

                def tratar_hora(h):
                    h = str(h).replace(":", "").strip()
                    try:
                        h_num = int(h)
                    except:
                        return h

                    if "2º Turno" in turno and 0 <= h_num <= 200:
                        return str(h_num + 2400)

                    return str(h_num)

                if "Hora" in df.columns:
                    df["Hora"] = df["Hora"].apply(tratar_hora)

                st.success("✅ Sucesso!")
                df_editado = st.data_editor(df, num_rows="dynamic", use_container_width=True)
                st.code(df_editado.to_csv(sep="\t", index=False), language="text")
                st.info("Copie e cole no Excel.")

            except Exception as e:
                st.error(f"Erro: {e}")
