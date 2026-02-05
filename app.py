import streamlit as st
import requests
import pandas as pd
import io
from PIL import Image
import base64

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Stellantis Scanner", page_icon="🏭", layout="wide")

# --- ESTILO VISUAL INDUSTRIAL DE ALTO CONTRASTE ---
st.markdown("""
<style>
    /* 1. Fundo Principal - Azul Stellantis Médio */
    .stApp {
        background-color: #243882;
        color: #ffffff;
    }

    /* 2. NOVO: Barra Lateral - Azul Stellantis Escuro */
    [data-testid="stSidebar"] {
        background-color: #00133b;
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }

    /* 3. Textos em Branco para Contraste (Geral e Sidebar) */
    h1, h2, h3, p, span, label, div[data-testid="stMarkdownContainer"] p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] h1 {
        color: #ffffff !important;
    }
    
    /* 4. NOVO: Botões de Ação (Upload e Processar) - AMARELO INDUSTRIAL */
    /* Isso garante contraste máximo contra o fundo azul */
    div.stButton > button, [data-testid="stFileUploader"] button {
        background-color: #FFC107 !important; /* Amarelo Amber vibrante */
        color: #000000 !important; /* Texto preto para leitura fácil */
        border: none !important;
        padding: 0.6rem 1rem;
        border-radius: 6px;
        font-weight: 800 !important; /* Negrito extra */
        text-transform: uppercase; /* Letras maiúsculas para destacar */
        letter-spacing: 0.05em;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3); /* Sombra para dar relevo */
    }
    
    /* Efeito ao passar o mouse nos botões */
    div.stButton > button:hover, [data-testid="stFileUploader"] button:hover {
        background-color: #FFD700 !important; /* Amarelo mais claro */
        box-shadow: 0 6px 12px rgba(0,0,0,0.4);
        transform: translateY(-2px); /* Leve movimento para cima */
    }

    /* 5. Seletores (Radio Buttons) - Melhorar visualização */
    div[role="radiogroup"] label {
        background-color: rgba(0, 19, 59, 0.6); /* Fundo azul escuro transparente */
        padding: 12px;
        border-radius: 8px;
        margin-right: 10px;
        border: 2px solid rgba(255, 255, 255, 0.2); /* Borda mais visível */
        font-weight: bold;
    }
    
    /* Ajuste para inputs de texto ficarem legíveis */
    .stTextInput input { color: #333333; background-color: #ffffff; }
</style>
""", unsafe_allow_html=True)

# --- CABEÇALHO ---
col1, col2 = st.columns([1, 6])
with col1:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/b/b5/Stellantis.svg/2560px-Stellantis.svg.png", width=120)
with col2:
    st.title("Digitalizador de Apontamento - SPW")
    st.markdown("**Automacao via Google Gemini (Industrial UI)**")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuração")
    api_key_input = st.text_input("Cole sua Gemini API Key:", type="password")
    api_key = api_key_input.strip() if api_key_input else ""
    st.markdown("---")
    st.info("Sistema operando em modo de alto contraste para ambiente fabril.")

if not api_key:
    st.warning("👈 Insira sua API Key na barra lateral escura para começar.")
    st.stop()

# --- SELETOR DE TURNO ---
st.divider()
st.subheader("1. Selecione o Turno Atual")
turno = st.radio(
    "Regra de cálculo de horas:",
    ["1º Turno (06:00 - 15:48)", "2º Turno (15:48 - 25:09)", "3º Turno (01:09 - 06:00)"],
    horizontal=True,
    index=1,
    label_visibility="collapsed" # Esconde o label pequeno repetido
)

# --- UPLOAD ---
st.markdown("### 2. Digitalizar Ficha")
uploaded_file = st.file_uploader("Carregue a imagem do apontamento abaixo:", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Visualização da Imagem", use_container_width=True)
    
    st.write("") # Espaçamento
    # Botão Principal de Ação
    if st.button("🚀 PROCESSAR APONTAMENTO AGORA"):
        with st.spinner("Lendo manuscrito e aplicando regras de negócio..."):
            try:
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='JPEG')
                img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode("utf-8")

                # URL v1 ESTÁVEL
                url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
                
                payload = {
                    "contents": [{
                        "parts": [
                            {"text": """
                                Atue como OCR industrial. Analise esta imagem.
                                Retorne APENAS um JSON (array de objetos) com:
                                "Data", "Maquina", "Hora", "Desenho", "Qtd_OK", "Qtd_NOK", "Cod_Parada".
                                Repita Data e Maquina do cabeçalho em todas as linhas.
                                Se hora tiver ':', mantenha. Se campos estiverem vazios, use string vazia.
                            """},
                            {"inline_data": {
                                "mime_type": "image/jpeg",
                                "data": img_base64
                            }}
                        ]
                    }]
                }
                
                response = requests.post(url, json=payload)
                
                if response.status_code != 200:
                    st.error(f"Erro na conexão com Google (Cód: {response.status_code})")
                    st.stop()
                
                result_json = response.json()
                try:
                    texto_resposta = result_json['candidates'][0]['content']['parts'][0]['text']
                    clean_json = texto_resposta.replace("```json", "").replace("```", "").strip()
                    df = pd.read_json(io.StringIO(clean_json))
                except Exception as e:
                    st.error("Não foi possível ler a tabela nesta imagem. Tente uma foto com melhor iluminação.")
                    st.stop()

                # REGRAS DE NEGÓCIO
                def tratar_hora(hora_str):
                    if not hora_str: return ""
                    h_limpa = str(hora_str).replace(":", "").strip()
                    try:
                        h_num = int(h_limpa)
                    except:
                        return h_limpa 
                    
                    if "2º Turno" in turno:
                        if 0 <= h_num <= 200:
                            return str(h_num + 2400)
                    return str(h_num)

                if "Hora" in df.columns:
                    df["Hora"] = df["Hora"].apply(tratar_hora)
                
                # EXIBIÇÃO
                st.success("✅ Leitura concluída com sucesso!")
                st.markdown("### 3. Verificar e Copiar")
                df_editado = st.data_editor(df, num_rows="dynamic", use_container_width=True)
                
                tsv = df_editado.to_csv(sep="\t", index=False)
                st.code(tsv, language="text")
                st.info("👆 Use o ícone de copiar no canto do bloco acima e cole no Excel.")
                
            except Exception as e:
                st.error(f"Erro inesperado: {e}")