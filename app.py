import streamlit as st
import requests
import pandas as pd
import io
from PIL import Image
import base64

# --- 1. CONFIGURAÇÃO DA PÁGINA (VISUAL LIMPO) ---
st.set_page_config(
    page_title="Stellantis Scanner Pro",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS INSPIRADO NO MEDIA.STELLANTIS.COM ---
st.markdown("""
<style>
    /* FUNDO GERAL - Branco/Cinza muito claro */
    .stApp {
        background-color: #f8f9fa;
        color: #212529;
    }

    /* BARRA LATERAL - Azul Noturno Stellantis */
    [data-testid="stSidebar"] {
        background-color: #0d1b2a;
        border-right: 1px solid #dee2e6;
    }
    
    /* TEXTOS NA SIDEBAR - Branco para contraste */
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] label, [data-testid="stSidebar"] span, [data-testid="stSidebar"] p {
        color: #ffffff !important;
    }

    /* BOTÕES - Azul Institucional Vibrante */
    div.stButton > button {
        background-color: #004481; /* Azul Stellantis */
        color: white;
        border: none;
        padding: 0.6rem 1.2rem;
        border-radius: 4px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        transition: all 0.2s ease-in-out;
        width: 100%;
    }
    div.stButton > button:hover {
        background-color: #002a50; /* Azul mais escuro no hover */
        color: white;
    }

    /* CAIXAS DE SELEÇÃO E INPUTS */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div, .stFileUploader {
        background-color: #ffffff;
        border: 1px solid #ced4da;
        border-radius: 4px;
        color: #495057;
    }

    /* TABELAS - Estilo limpo */
    [data-testid="stDataFrame"] {
        border: 1px solid #dee2e6;
        border-radius: 4px;
    }

    /* TITULOS PRINCIPAIS */
    h1, h2, h3 {
        color: #004481;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
    
    /* ESPAÇAMENTO (Margens que você pediu) */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 5rem;
    }
    
    /* LOGO CENTRALIZADA */
    [data-testid="stSidebar"] [data-testid="stImage"] {
        text-align: center;
        display: block;
        margin-left: auto;
        margin-right: auto;
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. GERENCIAMENTO DE ESTADO (MEMÓRIA) ---
# Isso impede que os dados sumam ao interagir com a tela
if 'tabela_final' not in st.session_state:
    st.session_state.tabela_final = pd.DataFrame()

# --- 4. BARRA LATERAL (CONFIGURAÇÕES) ---
with st.sidebar:
    # Tenta carregar a logo local, se não der, usa texto
    try:
        st.image("logo_azul-removebg-preview.png", width=180) 
    except:
        st.title("STELLANTIS")
    
    st.markdown("---")
    st.header("⚙️ Configuração")
    
    api_key = st.text_input("Chave API Gemini:", type="password")
    
    # Busca de Modelos
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
                    if 'generateContent' in m['supportedGenerationMethods'] and 'gemini' in m['name']
                ]
                st.success(f"Conectado! {len(modelos_disponiveis)} modelos disponíveis.")
        except:
            pass

    if modelos_disponiveis:
        # Tenta selecionar o Flash 2.0 ou Latest automaticamente
        idx = 0
        if "gemini-2.0-flash-001" in modelos_disponiveis:
            idx = modelos_disponiveis.index("gemini-2.0-flash-001")
        elif "gemini-flash-latest" in modelos_disponiveis:
            idx = modelos_disponiveis.index("gemini-flash-latest")
            
        modelo_selecionado = st.selectbox("Modelo IA:", modelos_disponiveis, index=idx)
    
    st.markdown("---")
    st.markdown("### 🕒 Turno")
    turno = st.radio(
        "Selecione para cálculo de horas:",
        ["1º Turno (06h-15h)", "2º Turno (15h-01h)", "3º Turno (01h-06h)"],
        index=1
    )
    
    if not st.session_state.tabela_final.empty:
        st.markdown("---")
        if st.button("🗑️ Limpar Tabela"):
            st.session_state.tabela_final = pd.DataFrame()
            st.rerun()

# --- 5. ÁREA PRINCIPAL ---
st.title("Digitalização de Apontamento - SPW")
st.markdown("Carregue múltiplas fotos para processar tudo de uma vez.")

if not api_key:
    st.warning("👈 Por favor, insira sua Chave API na barra lateral para começar.")
    st.stop()

# Upload Múltiplo
uploaded_files = st.file_uploader(
    "Arraste suas fotos aqui (JPG, PNG)", 
    type=['png', 'jpg', 'jpeg'], 
    accept_multiple_files=True
)

# Botão de Processar
if uploaded_files and modelo_selecionado:
    st.write(f"📂 {len(uploaded_files)} arquivos selecionados.")
    
    if st.button("🚀 PROCESSAR TODOS OS ARQUIVOS"):
        todas_as_leituras = []
        barra_progresso = st.progress(0)
        
        for i, uploaded_file in enumerate(uploaded_files):
            # Atualiza barra
            barra_progresso.progress((i + 1) / len(uploaded_files))
            
            try:
                # Prepara imagem
                image = Image.open(uploaded_file)
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='JPEG')
                img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode("utf-8")

                # Chama Gemini
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo_selecionado}:generateContent?key={api_key}"
                payload = {
                    "contents": [{
                        "parts": [
                            {"text": """Atue como OCR industrial. Retorne JSON array: "Data", "Maquina", "Hora", "Desenho", "Qtd_OK", "Qtd_NOK", "Cod_Parada". Repita Data/Maquina do topo em cada linha. Se hora tiver ':', mantenha."""},
                            {"inline_data": {"mime_type": "image/jpeg", "data": img_base64}}
                        ]
                    }]
                }
                
                response = requests.post(url, json=payload)
                if response.status_code == 200:
                    result = response.json()
                    texto = result['candidates'][0]['content']['parts'][0]['text']
                    clean_json = texto.replace("```json", "").replace("```", "").strip()
                    df_temp = pd.read_json(io.StringIO(clean_json))
                    todas_as_leituras.append(df_temp)
                else:
                    st.error(f"Erro no arquivo {uploaded_file.name}: {response.text}")
                    
            except Exception as e:
                st.error(f"Falha ao ler {uploaded_file.name}: {e}")

        # Consolida tudo
        if todas_as_leituras:
            df_consolidado = pd.concat(todas_as_leituras, ignore_index=True)
            
            # Aplica Regra de Turno no dataframe final
            def tratar_hora(h):
                h = str(h).replace(":", "").strip()
                try: h_num = int(h)
                except: return h
                if "2º Turno" in turno and 0 <= h_num <= 200: return str(h_num + 2400)
                return str(h_num)

            if "Hora" in df_consolidado.columns:
                df_consolidado["Hora"] = df_consolidado["Hora"].apply(tratar_hora)
            
            # Salva na memória do navegador
            st.session_state.tabela_final = df_consolidado
            st.success("✅ Leitura em lote concluída!")
            st.rerun() # Recarrega para mostrar a tabela fixa

# --- 6. EXIBIÇÃO DA TABELA (PERSISTENTE) ---
if not st.session_state.tabela_final.empty:
    st.markdown("### 📊 Resultado Consolidado")
    
    # Editor de dados (permite corrigir valores na tela)
    df_editado = st.data_editor(
        st.session_state.tabela_final, 
        num_rows="dynamic", 
        use_container_width=True,
        height=500 # Tabela mais alta para ver mais dados
    )
    
    st.markdown("### Copiar para Excel")
    st.info("Clique no ícone de copiar no canto superior direito do bloco abaixo:")
    st.code(df_editado.to_csv(sep="\t", index=False), language="text")

elif not uploaded_files:
    # Mensagem de boas vindas se não tiver nada carregado
    st.info("👆 Comece arrastando fotos para a área de upload acima.")