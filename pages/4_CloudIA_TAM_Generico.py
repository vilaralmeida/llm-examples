# https://langchain-ai.github.io/langgraph/#example

import os
from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI
from langchain.chains import GraphCypherQAChain
from langchain.graphs import Neo4jGraph
from langchain.prompts.prompt import PromptTemplate
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic
from langsmith import traceable
import streamlit as st

st.title("🦜 CloudIA - TAM Generico")
"""
Esse chat acessa uma base de conhecimento armazenada em um banco de dados de Grafo. Atualmente 
conta com arquivos compartilhados durante a composição da oferta de Multinuvem Oracle e Huawei.
pense nas perguntas seguindo o seguinte formato:
- Qual a especificacao do produto Oracle Autonomous JSON Database-ECPU ?
- Quais produtos são ofertados com capacidade de compute?
- Em qual ambiente está o produto Cloud Eye?
- Quais os valores praticados para o produto Logging Analytics?
"""

