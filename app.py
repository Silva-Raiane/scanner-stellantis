import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import io

# Configuração da Página
st.set_page_config(page_title="Stellantis Scanner", page_icon="🏭", layout="centered")

# Estilo Industrial (Dark Mode forçado pelo Streamlit Settings ou CSS)
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #00a8e8; color: white; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏭 Stellantis Production Scanner")
st.markdown("### Digitalização de Apontamento via Gemini AI")

# 1. Configuração da API Key
api_key = st.text_input("Cole sua Gemini API Key aqui:", type="password")

if api_key:
    genai.configure(api_key=api_key)
    
    # 2. Seletor de Turno
    turno = st.radio("Selecione o Turno Atual:", ["1º Turno (06:00 - 15:48)", "2º Turno (15:48 - 01:09)", "3º Turno (01:09 - 06:00)"], index=1)

    # 3. Upload
    uploaded_file = st.file_uploader("📸 Tire uma foto da ficha ou faça upload", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption='Ficha Carregada', use_container_width=True)

        if st.button("🚀 Processar Imagem"):
            with st.spinner('O Gemini está lendo a letra do operador...'):
                try:
                    # Lógica do Prompt para o Gemini
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    prompt = """
                    Você é um especialista em OCR industrial. Analise esta imagem de um apontamento de produção manuscrito.
                    Retorne APENAS um JSON (sem ```json no inicio) com uma lista de objetos contendo:
                    - "Hora": A hora escrita (Ex: 0600). Se for entre 00:00 e 01:59 e parecer ser final do dia, mantenha o original.
                    - "Desenho": O código numérico do produto.
                    - "Qtd_OK": Quantidade de peças boas (número).
                    - "Qtd_NOK": Quantidade de peças ruins (número).
                    - "Cod_Parada": Código da parada (texto ou número).
                    Ignore linhas vazias ou cabeçalhos.
                    """
                    
                    response = model.generate_content([prompt, image])
                    texto_resposta = response.text.replace("```json", "").replace("```", "").strip()
                    
                    # Converte JSON para Tabela (DataFrame)
                    df = pd.read_json(io.StringIO(texto_resposta))
                    
                    # --- APLICANDO A REGRA DE NEGÓCIO DA RAIANE ---
                    # Remove dois pontos e aplica regra de 25h se for 2º turno
                    def corrigir_hora(h):
                        h = str(h).replace(":", "")
                        if "2º Turno" in turno:
                            try:
                                h_num = int(h)
                                if 0 <= h_num <= 200: # Se for entre 00:00 e 02:00
                                    return str(h_num + 2400)
                            except:
                                pass
                        return h

                    if 'Hora' in df.columns:
                        df['Hora'] = df['Hora'].apply(corrigir_hora)
                    
                    # Mostra Tabela Editável
                    st.success("Leitura Concluída! Verifique os dados abaixo:")
                    df_editado = st.data_editor(df, num_rows="dynamic")

                    # Botão de Copiar
                    tsv = df_editado.to_csv(sep='\t', index=False)
                    st.code(tsv, language="text")
                    st.info("👆 Clique no ícone de copiar acima e cole no Excel (Ctrl+V)!")

                except Exception as e:
                    st.error(f"Erro na leitura: {e}. Tente tirar uma foto mais clara.")
else:
    st.warning("👈 Por favor, insira sua API Key para começar.")