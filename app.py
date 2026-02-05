import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import io

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Stellantis Scanner", page_icon="🏭", layout="wide")

# ESTILO VISUAL: AZUL STELLANTIS (#243882)
st.markdown("""
<style>
    /* Fundo Principal - Azul da Marca */
    .stApp {
        background-color: #243882;
        color: #ffffff;
    }
    
    /* Textos em Branco para Contraste */
    h1, h2, h3, p, span, label, div[data-testid="stMarkdownContainer"] p {
        color: #ffffff !important;
    }
    
    /* Botões: Fundo Branco com Texto Azul */
    div.stButton > button {
        background-color: #ffffff;
        color: #243882;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        font-weight: bold;
        width: 100%;
        transition: all 0.3s;
    }
    div.stButton > button:hover {
        background-color: #e0e0e0;
        color: #243882;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }

    /* Seletores (Radio Buttons) */
    div[role="radiogroup"] label {
        background-color: rgba(255, 255, 255, 0.1);
        padding: 10px;
        border-radius: 5px;
        margin-right: 10px;
        border: 1px solid rgba(255,255,255,0.2);
    }
    
    /* Inputs de Texto */
    .stTextInput input {
        color: #000000;
    }
</style>
""", unsafe_allow_html=True)

# --- CABEÇALHO ---
col1, col2 = st.columns([1, 6])
with col1:
    # Logo oficial (URL pública confiável)
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/b/b5/Stellantis.svg/2560px-Stellantis.svg.png", width=120)
with col2:
    st.title("Digitalizador de Apontamento - SPW")
    st.markdown("**Automacao de Leitura via Google Gemini AI**")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuração")
    api_key = st.text_input("Cole sua Gemini API Key:", type="password")
    st.info("Sua chave não será salva permanentemente.")

# --- LÓGICA PRINCIPAL ---
if not api_key:
    st.warning("👈 Insira sua API Key na barra lateral esquerda para ativar o sistema.")
    st.stop()

genai.configure(api_key=api_key)

st.divider()

# 1. SELETOR DE TURNO
st.subheader("1. Selecione o Turno Atual")
turno = st.radio(
    "Defina a regra de horário:",
    ["1º Turno (06:00 - 15:48)", "2º Turno (15:48 - 25:09)", "3º Turno (01:09 - 06:00)"],
    horizontal=True
)

# 2. UPLOAD
st.subheader("2. Digitalizar Ficha")
uploaded_file = st.file_uploader("Tire uma foto ou carregue o arquivo", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Imagem Carregada", use_container_width=True)
    
    if st.button("🚀 Processar Apontamento"):
        with st.spinner("Lendo manuscrito... (Isso leva uns 5 segundos)"):
            try:
                # MODELO ATUALIZADO
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                prompt = """
                Atue como um especialista em OCR industrial.
                Analise esta imagem de apontamento de produção.
                
                TAREFA: Extraia todas as linhas da tabela de produção.
                Para cada linha, encontre a DATA e MÁQUINA no cabeçalho da folha e repita em cada linha.
                
                SAÍDA: Retorne APENAS um JSON (array de objetos) com as chaves:
                "Data", "Maquina", "Hora", "Desenho", "Qtd_OK", "Qtd_NOK", "Cod_Parada".
                
                Regras de Leitura:
                - Se "Hora" tiver dois pontos (Ex: 06:00), mantenha com os dois pontos por enquanto.
                - Se campos estiverem vazios, use string vazia.
                """
                
                response = model.generate_content([prompt, image])
                json_str = response.text.replace("```json", "").replace("```", "").strip()
                
                df = pd.read_json(io.StringIO(json_str))
                
                # --- REGRAS DE NEGÓCIO (PYTHON) ---
                def tratar_hora(hora_str):
                    if not hora_str: return ""
                    # Regra 1: Remover :
                    h_limpa = str(hora_str).replace(":", "").strip()
                    try:
                        h_num = int(h_limpa)
                    except:
                        return h_limpa 
                    
                    # Regra 2: Lógica do 2º Turno (Madrugada vira 25h)
                    if "2º Turno" in turno:
                        # Se for entre 0000 e 0200, soma 2400
                        if 0 <= h_num <= 200:
                            return str(h_num + 2400)
                    
                    return str(h_num)

                if "Hora" in df.columns:
                    df["Hora"] = df["Hora"].apply(tratar_hora)
                
                # Ordenação das colunas
                cols = ["Data", "Maquina", "Hora", "Desenho", "Qtd_OK", "Qtd_NOK", "Cod_Parada"]
                for c in cols:
                    if c not in df.columns: df[c] = ""
                df = df[cols]

                st.success("✅ Leitura concluída!")
                st.markdown("### 3. Verificar e Editar")
                df_editado = st.data_editor(df, num_rows="dynamic", use_container_width=True)
                
                st.markdown("### 4. Copiar para Excel")
                csv = df_editado.to_csv(sep="\t", index=False)
                st.code(csv, language="text")
                st.info("👆 Clique no ícone de copiar acima e cole no Excel.")
                
            except Exception as e:
                st.error(f"Erro: {e}")
                st.warning("Dica: Se o erro for 404, reinicie o app no menu superior direito.")