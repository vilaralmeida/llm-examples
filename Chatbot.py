from openai import OpenAI
import anthropic
from dotenv import load_dotenv
import streamlit as st
import asyncio
from utils import (
    updateFile, 
    solicitaCargaBaseConhecimento, 
    listaDocumentos, 
    verificaDocumento, 
    getEstruturas, 
    getRecursos, 
    get_structure_prompt, 
    get_recurso_narrativo, 
    digitaPrompt,
    getPersonagens,
    getFatos,
    get_prompt_fato,
    carrega_fatos,
    get_prompt_personagem,
    get_instrucoes
)
from streamlit_quill import st_quill
import json
import time
import re
from dataclasses import dataclass
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ModelMessage
from pydantic_ai.usage import Usage, UsageLimits
from pydantic_ai import Agent, RunContext
from pydantic_ai.usage import UsageLimits
from typing import Dict, List, Union
from pydantic import BaseModel, Field
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.providers.deepseek import DeepSeekProvider
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.providers.google_gla import GoogleGLAProvider

load_dotenv()

if 'openai_api_key' not in st.session_state:
    st.session_state.openai_api_key = None
    
if 'anthropic_api_key' not in st.session_state:
    st.session_state.anthropic_api_key = None

if 'deepseek_api_key' not in st.session_state:
    st.session_state.deepseek_api_key = None    

if 'gemini_api_key' not in st.session_state:
    st.session_state.gemini_api_key = None  

if 'openai_model' not in st.session_state:
    st.session_state.openai_model = None

if 'anthropic_model' not in st.session_state:
    st.session_state.anthropic_model = None  
    
if 'deepseek_model' not in st.session_state:
    st.session_state.deepseek_model = None      
    
if 'gemini_model' not in st.session_state:
    st.session_state.gemini_model = None 
    
if 'recurso' not in st.session_state:    
    st.session_state.recurso = None  

if 'estrutura' not in st.session_state:    
    st.session_state.estrutura = None  
    
if 'conteudo_digitado' not in st.session_state:   
    st.session_state.conteudo_digitado = None  

if 'proposta_selecionada' not in st.session_state:   
    st.session_state.proposta_selecionada = None   
    
if 'narrativa' not in st.session_state:
   st.session_state.narrativa = None 
   
if 'autor' not in st.session_state:
    st.session_state.autor = "rodrigo.almeida@gmail.com"        

if 'personagem' not in st.session_state:
    st.session_state.personagem = None
    
if 'fato' not in st.session_state:
    st.session_state.fato = None    
    
if 'provedor' not in st.session_state:
    st.session_state.provedor = None

if 'idioma' not in st.session_state:
    st.session_state.idioma = None

if 'modelOpenAI' not in st.session_state:
    st.session_state.modelOpenAI = None    

if 'modelAnthropic' not in st.session_state:
    st.session_state.modelAnthropic = None 
    
if 'modelDeepseek' not in st.session_state:
    st.session_state.modelDeepseek = None 

if 'modelGemini' not in st.session_state:
    st.session_state.modelGemini = None     
                
if 'num_propostas' not in st.session_state:
    st.session_state.num_propostas = 3    
            
if 'narrativas' not in st.session_state:
    st.session_state['narrativas'] = []

OPENAI_MODELS_1 = ("gpt-4.1-2025-04-14", "gpt-4.1-mini-2025-04-14", "gpt-4.1-nano-2025-04-14",
                   "gpt-4o-2024-08-06", "gpt-4o-2024-11-20", "gpt-4o-2024-08-06",
                   "gpt-4o-realtime-preview-2024-12-17", "gpt-4o-realtime-preview-2024-10-01",
                   "gpt-4o-mini-2024-07-18", "gpt-4o-mini-realtime-preview-2024-12-17",
                   "o1-2024-12-17", "o1-preview-2024-09-12", "o3-2025-04-16", "o4-mini-2025-04-16",
                   "o3-mini-2025-01-31", "o1-mini-2024-09-12" , "--- PREMIUM MODELS ---", "o1-pro-2025-03-19", "gpt-4.5-preview-2025-02-27")


GEMINI_MODELS = ("gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-flash", "gemini-1.5-flash-8b", "gemini-1.5-pro")

OPENAI_MODELS = ("gpt-4.1-2025-04-14", "gpt-4.1-mini-2025-04-14", "gpt-4.1-nano-2025-04-14",
                   "gpt-4o-2024-08-06", "gpt-4o-2024-11-20", "gpt-4o-2024-08-06",
                   "gpt-4o-realtime-preview-2024-12-17", "gpt-4o-realtime-preview-2024-10-01",
                   "gpt-4o-mini-2024-07-18", "gpt-4o-mini-realtime-preview-2024-12-17",
                   "o1-2024-12-17", "o1-preview-2024-09-12", "o4-mini-2025-04-16",
                   "o3-mini-2025-01-31", "o1-mini-2024-09-12" , "--- PREMIUM MODELS ---", "o1-pro-2025-03-19", "gpt-4.5-preview-2025-02-27")


# ANTHROPIC_MODELS = ("claude-opus-4-20250514", "claude-sonnet-4-20250514", "claude-3-7-sonnet-20250219", "claude-3-5-haiku-20241022")
ANTHROPIC_MODELS = ("claude-3-5-haiku-20241022")

DEEPSEEK_MODELS = ("deepseek-chat")

st.set_page_config(page_title='👾 VFN 1.0', layout='wide',
    #    initial_sidebar_state=st.session_state.get('sidebar_state', 'collapsed'),
)



with st.sidebar:
    st.session_state.openai_api_key = st.text_input("OpenAI API Key", key="chat_openai_api_key", type="password")
    "[OpenAI Models Overview](https://platform.openai.com/docs/models)"
    st.session_state.anthropic_api_key = st.text_input("Anthropic API Key", key="chat_anthropic_api_key", type="password")    
    "[Anthropic Models Overview](https://docs.anthropic.com/en/docs/about-claude/models/overview)"
    st.session_state.deepseek_api_key = st.text_input("DeepSeek API Key", key="chat_deepseek_api_key", type="password")    
    "[DeepSeek Models Overview](https://api-docs.deepseek.com/quick_start/pricing)"    
    st.session_state.gemini_api_key = st.text_input("Gemini API Key", key="chat_gemini_api_key", type="password")    
    "[Gemini Models Overview](https://ai.google.dev/gemini-api/docs/models)"     
    

# Classe com parametros necessários para construção das propostas narrativas
@dataclass
class SupportDependencies:  
    narrativa: str
    personagem: str
    fatos: str
    structure_prompt: str
    recurso: str
    count: int
    idioma: str

class SupportResult(BaseModel):
    titulo: str = Field(description='Um titulo que resume a proposta.')    
    proposta: str = Field(description='Ideia que deverá evoluir com base na estrutura e recurso narrativo sugerido pelo usuário.')
    impacto: str = Field(description='Como a ideia impacta a jornada do personagem')
    abordagem_estrutural: str = Field(description="De que forma a ideia está relacionada à abordagem estrutural proposta? (Ex.: A alternância emocional é alcançada através das indecisões do personagem .....)")
    recurso_narrativo: str = Field(description="De que forma o recurso narrativo foi abordado? (ex.: incluí a Alegoria ao sugerir que o amor fosse representado através da relação entre o algodão e a desfiadeira....)")
    lugar_comum: str = Field(description='Como a proposta sugerida evita que o escritor caia no lugar comum em relação a seu conteúdo?')


class Extraction(BaseModel):
    Support_Result: List[SupportResult] = Field(description="List of Support Results")    

@st.fragment() 
def getTitulosPropostas():
    result = []
    for i in range(len(st.session_state['narrativas'])):
        result.append(st.session_state['narrativas'][i]["titulo"])        
    return result    

@st.fragment() 
def getNarrativaSelecionada():
    result = None
    for i in range(len(st.session_state['narrativas'])):
        if st.session_state['narrativas'][i]["titulo"] == st.session_state.proposta_selecionada:
            result = st.session_state['narrativas'][i]
            break              
    return result    
    

@st.fragment() 
def trecho5():
    with st.chat_message("assistant"):   
        st.write(digitaPrompt("🛺 Selecione o Título da Proposta que você gostaria de ver a história completa:")) 

@st.fragment() 
def escolheNarrativa():
    texto = "🧚🏼‍♀️"  
    trecho5()
    titulos = getTitulosPropostas()
    cols_titulos_propostas = st.columns(len(titulos))  
    for j, option_titulos_propostas in enumerate(titulos):                        
        if cols_titulos_propostas[j].button(option_titulos_propostas):
            st.session_state.proposta_selecionada = option_titulos_propostas                           
    if st.session_state.proposta_selecionada is not None:
        texto =  f"""🧚🏼‍♀️ Proposta Selecionada: {st.session_state.proposta_selecionada}"""
        st.info(texto)        
        nova_historia_texto = getNarrativaSelecionada()
        # st.write(nova_historia_texto)
        
        prompt_instrucoes = get_instrucoes(nova_historia=nova_historia_texto,
                                                          idioma=st.session_state.idioma)        
        
        result_narrativa = None
        
        if (st.session_state.provedor == "ANTHROPIC"):
            support_agent_anthropic_narrativa = Agent(  
                st.session_state.modelAnthropic, 
                system_prompt=(  
                    "Você é um ajudante na jornada de um escritor em melhorar a escrita de seu conteúdo."            
                ),
                retries=2,
            )             
            with st.spinner(f"[ANTHROPIC {st.session_state.anthropic_model}] Gerando Narrativa....", show_time=True):    
                result_narrativa = support_agent_anthropic_narrativa.run_sync(prompt_instrucoes)
                while result_narrativa is None:        
                    time.sleep(1) 
                            
        if (st.session_state.provedor == "OPENAI"):
            support_agent_openai_narrativa = Agent(   
                st.session_state.modelOpenAI,
                system_prompt=(  
                    "Você é um ajudante na jornada de um escritor em melhorar a escrita de seu conteúdo."
                ),
                retries=2,
            )               
            with st.spinner(f"[OPENAI {st.session_state.openai_model}] Gerando Narrativa....", show_time=True):    
                result_narrativa = support_agent_openai_narrativa.run_sync(prompt_instrucoes)
                while result_narrativa is None:        
                    time.sleep(1)            
                     
        if (st.session_state.provedor == "GEMINI"):
            support_agent_gemini_narrativa = Agent(  
                st.session_state.modelGemini, 
                system_prompt=(  
                    "Você é um ajudante na jornada de um escritor em melhorar a escrita de seu conteúdo."
                ),
                retries=2,
            )                
            with st.spinner(f"[GEMINI {st.session_state.gemini_model}] Gerando Narrativa....", show_time=True):    
                result_narrativa = support_agent_gemini_narrativa.run_sync(prompt_instrucoes)
                while result_narrativa is None:        
                    time.sleep(1)    

        if (st.session_state.provedor == "DEEPSEEK"):
            support_agent_deepseek_narrativa = Agent(  
                st.session_state.modelDeepseek, 
                system_prompt=(  
                    "Você é um ajudante na jornada de um escritor em melhorar a escrita de seu conteúdo."            
                ),
                retries=2,
            )                                 
            with st.spinner(f"[DEEPSEEK {st.session_state.deepseek_model}] Gerando Narrativa....", show_time=True):    
                result = support_agent_deepseek_narrativa.run_sync(prompt_instrucoes)
                while result_narrativa is None:        
                    time.sleep(1)                              

        st.write(result_narrativa.output)                     


async def chat():  
    st.title("💬 Validador de Fluxo Narrativo - VFN 1.0")
    with st.expander("Cadastrar Narrativa Base"):
        title = st.text_input("Título (evite caracteres especiais no título):", "")        
        st.session_state.conteudo_digitado = st_quill()   
        if st.button("Carregar", type="primary"):
            updateFile(title, st.session_state.autor, st.session_state.conteudo_digitado)
            solicitaCargaBaseConhecimento(title, st.session_state.autor,"NOVA_NARRATIVA","PT", "story_teller")   
            with st.spinner("Carregando Base de Conhecimento....", show_time=True):    
                while not verificaDocumento(title, st.session_state.autor):        
                    time.sleep(1)
                st.success("File successfully uploaded!")

    container = st.container(border=True)
    with container:
        options = listaDocumentos(st.session_state.autor)
        # cols = st.columns(len(options))
        st.session_state.narrativa = st.selectbox("Selecione uma Narrativa:", options=options, index=0, 
                                            help=f"Narrativas Carregadas pelo Autor", key="narrativa_box")    

        if st.session_state.narrativa is not None:
            col1, col2 = st.columns([1,1])  
            with col1:
                options_personagem = getPersonagens(st.session_state.autor, st.session_state.narrativa)
                st.session_state.personagem = st.selectbox("Selecione um Personagem:", options=options_personagem, index=0, 
                                            help=f"Personagens presentes na narrativa {st.session_state.narrativa}", key="personagem_box")    
            with col2:    
                options_fatos = getFatos(st.session_state.autor, st.session_state.narrativa)
                st.session_state.fato = st.selectbox("Selecione um Fato:", options=options_fatos, index=0, 
                                            help=f"Fatos presentes na narrativa {st.session_state.narrativa}")        
        col1, col2 = st.columns([1,1])    
        with col1:
            select_col, exp_col = st.columns([2,6])
            with select_col:
                st.session_state.estrutura = st.selectbox("Selecione um Estrutura:", options=getEstruturas(), index=0, 
                                            help=f"Estruturas para construção Narrativa. Fique atento à qual melhor se adequa ao seu objetivo.", key="estrutura_box")                        
            with exp_col:
                if st.session_state.estrutura is not None:
                    with st.expander(f"**📖 O que significa a estrutura {st.session_state.estrutura}?**"):
                        st.markdown(get_structure_prompt(st.session_state.estrutura))    
            
        with col2:
            select_col, exp_col = st.columns([2,6])
            with select_col:
                st.session_state.recurso = st.selectbox("Selecione um Recurso:", options=getRecursos(), index=0, 
                                            help=f"Recursos para construção Narrativa. Fique atento à qual melhor se adequa ao seu objetivo.", key="recurso_box")                        
            with exp_col:
                if st.session_state.recurso is not None:
                    with st.expander(f"**📖 O que significa  recurso {st.session_state.recurso}?**"):
                        st.markdown(get_recurso_narrativo(st.session_state.recurso))   
            

        col1, col2, col3, col4 = st.columns([1,1,1,1])    
        with col1:
            st.session_state.openai_model = st.selectbox("Modelo OpenAI:",OPENAI_MODELS_1, key="openai_model_box")
        with col2:  
            st.session_state.anthropic_model = st.selectbox("Modelo Anthropic:",ANTHROPIC_MODELS,key="anthropic_model_box")  
        with col3:              
            st.session_state.deepseek_model = st.selectbox("Modelo DeepSeek:",DEEPSEEK_MODELS,key="deepseek_model_box")  
        with col4:              
            st.session_state.gemini_model = st.selectbox("Modelo Gemini:",GEMINI_MODELS,key="gemini_model_box")
            
        col1, col2 = st.columns([1,1])  
        with col1:
            st.session_state.idioma = st.selectbox("Selecione o Idioma:",("PORTUGUES", "INGLES", "ESPANHOL", "ITALIANO", "FRANCES"),key="idiomas_box")
        with col2:
            st.session_state.provedor = st.selectbox("Selecione um Provedor de Modelos de IA:",("OPENAI", "ANTHROPIC", "DEEPSEEK", "GEMINI"),key="provedores_box")    


    if st.button("Gerar Propostas Narrativas", type="primary"):
        if st.session_state.openai_api_key is None or st.session_state.anthropic_api_key is None or st.session_state.gemini_api_key is None or st.session_state.deepseek_api_key is None:
            st.write(digitaPrompt("Please add API key to continue."))
            st.stop()        
        results = []
        fatos = carrega_fatos(st.session_state.narrativa, st.session_state.personagem, st.session_state.autor)  
        prompt_recurso = get_recurso_narrativo(st.session_state.recurso)
        prompt_estrutura =  get_structure_prompt(st.session_state.estrutura)     
        deps = SupportDependencies(st.session_state.narrativa, 
                                st.session_state.personagem, 
                                fatos, 
                                prompt_estrutura, 
                                prompt_recurso, 
                                st.session_state.num_propostas,
                                st.session_state.idioma)
        
        prompt = get_prompt_personagem(count=st.session_state.num_propostas,
                                                                    personagem=st.session_state.personagem,  
                                                                    narrativa=st.session_state.narrativa,
                                                                    structure=prompt_estrutura,
                                                                    facts=fatos,
                                                                    recurso=prompt_recurso,
                                                                    idioma=st.session_state.idioma)        
                
        
        result = None
        
        if (st.session_state.provedor == "GEMINI"):
            st.write(digitaPrompt(f"🙅🏽‍♀️ Ok! A partir de agora vamos apresentar as propostas {st.session_state.narrativa}. Narrativas geradas com o Provedor {st.session_state.provedor} usando o modelo {st.session_state.gemini_model}" ))   
            st.session_state.modelGemini = GeminiModel(st.session_state.gemini_model, provider=GoogleGLAProvider(api_key=st.session_state.gemini_api_key))
            support_agent_gemini = Agent(  
                st.session_state.modelGemini, 
                deps_type=SupportDependencies,
                result_type=Extraction,  
                system_prompt=(  
                "Voce é um agente de suporte responsável por criar narrativas."            
                ),
                retries=2,
            )              
            with st.spinner(f"[GEMINI {st.session_state.gemini_model}] Gerando Propostas....", show_time=True):    
                result = await support_agent_gemini.run(prompt)
                while result is None:        
                    time.sleep(1)        

        if (st.session_state.provedor == "OPENAI"):
            st.write(digitaPrompt(f"🙅🏽‍♀️ Ok! A partir de agora vamos apresentar as propostas {st.session_state.narrativa}. Narrativas geradas com o Provedor {st.session_state.provedor} usando o modelo {st.session_state.openai_model}" ))   
            st.session_state.modelOpenAI = OpenAIModel(st.session_state.openai_model, provider=OpenAIProvider(api_key=st.session_state.openai_api_key))
            support_agent_openai = Agent(   
                st.session_state.modelOpenAI,
                deps_type=SupportDependencies,
                result_type=Extraction,  
                system_prompt=(  
                "Voce é um agente de suporte responsável por criar narrativas."            
                ),
                retries=2,
            )            
            with st.spinner(f"[OPENAI {st.session_state.openai_model}] Gerando Propostas....", show_time=True):    
                result = await support_agent_openai.run(prompt)
                while result is None:        
                    time.sleep(1)        
                    
        if (st.session_state.provedor == "ANTHROPIC"):
            st.write(digitaPrompt(f"🙅🏽‍♀️ Ok! A partir de agora vamos apresentar as propostas {st.session_state.narrativa}. Narrativas geradas com o Provedor {st.session_state.provedor} usando o modelo {st.session_state.anthropic_model}" ))   
            st.session_state.modelAnthropic  = AnthropicModel(st.session_state.anthropic_model, provider=AnthropicProvider(api_key=st.session_state.anthropic_api_key))
            support_agent_anthropic = Agent(  
                st.session_state.modelAnthropic, 
                deps_type=SupportDependencies,
                output_type=Extraction,  
                system_prompt=(  
                "Voce é um agente de suporte responsável por criar narrativas. "            
                ),
                retries=2,
            )              
            with st.spinner(f"[ANTHROPIC {st.session_state.anthropic_model}] Gerando Propostas....", show_time=True):    
                result = await support_agent_anthropic.run(prompt)
                while result is None:        
                    time.sleep(1)                         
        
        if (st.session_state.provedor == "DEEPSEEK"):
            st.write(digitaPrompt(f"🙅🏽‍♀️ Ok! A partir de agora vamos apresentar as propostas {st.session_state.narrativa}. Narrativas geradas com o Provedor {st.session_state.provedor} usando o modelo {st.session_state.deepseek_model}" ))   
            st.session_state.modelDeepseek = OpenAIModel(st.session_state.deepseek_model, provider=DeepSeekProvider(api_key=st.session_state.deepseek_api_key ),)
            support_agent_deepseek = Agent(  
                st.session_state.modelDeepseek, 
                deps_type=SupportDependencies,
                result_type=Extraction,  
                system_prompt=(  
                "Voce é um agente de suporte responsável por criar narrativas."            
                ),
                retries=2,
            )            
            with st.spinner(f"[DEEPSEEK {st.session_state.deepseek_model}] Gerando Propostas....", show_time=True):    
                result = await support_agent_deepseek.run(prompt)
                while result is None:        
                    time.sleep(1) 
                            
        with open("content223.txt", "w", encoding="utf-8") as f:
            f.write(str(result.output)) 
        with open("content223.txt", "r", encoding="utf-8") as file:
            # Read the contents of the file
            content = file.read()   
            content = content.strip() 
            # Regular expression to match each SupportResult block
            pattern = r"SupportResult\((.*?)\)"

            # Find all matches
            matches = re.findall(pattern, content, re.DOTALL)

            # Process each match into a dictionary
            
            for match in matches:
                fields = re.findall(r"(\w+)=\'(.*?)\'", match, re.DOTALL)
                result_dict = {key: value for key, value in fields}
                results.append(result_dict)
        st.session_state['narrativas'] = results
        st.write(st.session_state['narrativas']) 
        escolheNarrativa()



if __name__ == "__main__":
    asyncio.run(chat())