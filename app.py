import streamlit as st
import requests
import pandas as pd
import io
from PIL import Image
import base64

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Stellantis Scanner Pro",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS (Visual Media Stellantis) ---
st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; color: #212529; }
    [data-testid="stSidebar"] { background-color: #0d1b2a; border-right: 1px solid #dee2e6; }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] label, [data-testid="stSidebar"] span, [data-testid="stSidebar"] p { color: #ffffff !important; }
    div.stButton > button { background-color: #004481; color: white; border: none; padding: 0.6rem 1.2rem; border-radius: 4px; font-weight: 600; text-transform: uppercase; width: 100%; transition: all 0.2s; }
    div.stButton > button:hover { background-color: #002a50; color: white; }
    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div, .stFileUploader { background-color: #ffffff; border: 1px solid #ced4da; border-radius: 4px; color: #495057; }
    [data-testid="stDataFrame"] { border: 1px solid #dee2e6; border-radius: 4px; }
    h1, h2, h3 { color: #004481; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }
    .block-container { padding-top: 2rem; padding-bottom: 5rem; }
    [data-testid="stSidebar"] [data-testid="stImage"] { display: block; margin-left: auto; margin-right: auto; }
</style>
""", unsafe_allow_html=True)

# --- 3. GERENCIAMENTO DE ESTADO ---
if 'tabela_final' not in st.session_state:
    st.session_state.tabela_final = pd.DataFrame()

# --- 4. BARRA LATERAL ---
with st.sidebar:
    try:
        st.image("logo_azul-removebg-preview.png", width=180) 
    except:
        st.title("STELLANTIS")
    
    st.markdown("---")
    st.header("⚙️ Configuração")
    
    api_key = st.text_input("Chave API Gemini:", type="password")
    
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
                st.success(f"Conectado! {len(modelos_disponiveis)} modelos.")
        except:
            pass

    if modelos_disponiveis:
        idx = 0
        if "gemini-2.0-flash-001" in modelos_disponiveis:
            idx = modelos_disponiveis.index("gemini-2.0-flash-001")
        elif "gemini-flash-latest" in modelos_disponiveis:
            idx = modelos_disponiveis.index("gemini-flash-latest")
        modelo_selecionado = st.selectbox("Modelo IA:", modelos_disponiveis, index=idx)
    
    st.markdown("---")
    st.markdown("### 🕒 Turno")
    turno = st.radio(
        "Selecione:",
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
st.markdown("Carregue as fichas de produção para digitalizar.")

if not api_key:
    st.warning("👈 Insira sua Chave API na barra lateral.")
    st.stop()

uploaded_files = st.file_uploader(
    "Arraste suas fotos aqui (JPG, PNG)", 
    type=['png', 'jpg', 'jpeg'], 
    accept_multiple_files=True
)

if uploaded_files and modelo_selecionado:
    st.write(f"📂 {len(uploaded_files)} arquivos na fila.")
    
    if st.button("🚀 PROCESSAR TODOS"):
        todas_as_leituras = []
        barra = st.progress(0)
        
        for i, uploaded_file in enumerate(uploaded_files):
            barra.progress((i + 1) / len(uploaded_files))
            try:
                image = Image.open(uploaded_file)
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='JPEG')
                img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode("utf-8")

                url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo_selecionado}:generateContent?key={api_key}"
                
                # --- PROMPT ATUALIZADO: PEDINDO DUAS COLUNAS DE HORA ---
                prompt_texto = """
                Atue como OCR industrial. Analise a tabela manuscrita.
                Retorne APENAS um JSON array com os objetos.
                Campos obrigatórios: "Data", "Maquina", "Hora_Inicio", "Hora_Fim", "Desenho", "Qtd_OK", "Qtd_NOK", "Cod_Parada".
                
                Regras:
                1. Repita a Data e Máquina do cabeçalho em todas as linhas.
                2. Separe o intervalo de hora em "Hora_Inicio" e "Hora_Fim". Ex: se estiver escrito "06:00 - 07:00", Inicio="06:00", Fim="07:00".
                3. Se a hora tiver ':', mantenha.
                """

                payload = {
                    "contents": [{
                        "parts": [
                            {"text": prompt_texto},
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

        if todas_as_leituras:
            df_consolidado = pd.concat(todas_as_leituras, ignore_index=True)
            
            # --- REGRA DE HORAS PARA AS DUAS COLUNAS ---
            def tratar_hora(h):
                if pd.isna(h) or h == "": return ""
                h = str(h).replace(":", "").strip()
                try: h_num = int(h)
                except: return h
                # Se for 2º turno e a hora for entre 00:00 e 02:00, soma 2400 (virada do dia)
                if "2º Turno" in turno and 0 <= h_num <= 250: 
                    return str(h_num + 2400)
                return str(h_num)

            # Aplica a regra nas duas colunas se elas existirem
            for col in ["Hora_Inicio", "Hora_Fim"]:
                if col in df_consolidado.columns:
                    df_consolidado[col] = df_consolidado[col].apply(tratar_hora)
            
            # Reordenar colunas para ficar bonito
            cols_ordem = ["Data", "Maquina", "Hora_Inicio", "Hora_Fim", "Desenho", "Qtd_OK", "Qtd_NOK", "Cod_Parada"]
            # Garante que só pegamos colunas que realmente existem no DF (para evitar erro se a IA esquecer alguma)
            cols_finais = [c for c in cols_ordem if c in df_consolidado.columns]
            df_consolidado = df_consolidado[cols_finais]

            st.session_state.tabela_final = df_consolidado
            st.success("✅ Leitura concluída com separação de horas!")
            st.rerun()

# --- 6. EXIBIÇÃO DA TABELA ---
if not st.session_state.tabela_final.empty:
    st.markdown("### 📊 Resultado Consolidado")
    
    df_editado = st.data_editor(
        st.session_state.tabela_final, 
        num_rows="dynamic", 
        use_container_width=True,
        height=500
    )
    
    st.markdown("### Copiar para Excel")
    st.info("Clique no ícone de copiar no canto superior direito da tabela abaixo:")
    st.code(df_editado.to_csv(sep="\t", index=False), language="text")

elif not uploaded_files:
    st.info("👆 Faça o upload das fotos para começar.")