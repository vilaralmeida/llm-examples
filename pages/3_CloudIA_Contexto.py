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

st.title("🔗 CloudIA - Contexto")
"""
Esse chat acessa uma base de conhecimento armazenada em um banco de dados de Grafo. Atualmente 
conta com arquivos compartilhados durante a composição da oferta de Multinuvem Oracle e Huawei.
pense nas perguntas seguindo o seguinte formato:
- Qual a especificacao do produto Oracle Autonomous JSON Database-ECPU ?
- Quais produtos são ofertados com capacidade de compute?
- Em qual ambiente está o produto Cloud Eye?
- Quais os valores praticados para o produto Logging Analytics?
"""
load_dotenv()

CYPHER_GENERATION_TEMPLATE = """
Task:Generate Cypher statement to query a graph database.
Instructions:
Use only the provided relationship types and properties in the schema.
Do not use any other relationship types or properties that are not provided.
Schema:
{schema}
Cypher examples:
# Qual a especificacao do produto Oracle Autonomous JSON Database-ECPU ?
MATCH (p:Produto)-[:ESPECIFICADO_COMO]->(e:Especificacao)
WHERE toLower(p.name) CONTAINS toLower("Oracle Autonomous JSON Database-ECPU")
RETURN collect(DISTINCT e.name) as especificacoes;
# Quais os valores praticados para o produto Logging Analytics?
MATCH (p:Produto)-[:VALOR_MENSAL_REAL_PRODUTO]->(v:VALOR_MENSAL_REAL)
WHERE toLower(p.name) CONTAINS toLower("Logging Analytics")
RETURN collect(DISTINCT v.name) as valores;
# Quais produtos são ofertados com capacidade de compute?
MATCH (p:Produto)
WHERE toLower(p.name) CONTAINS toLower("compute")
RETURN collect(DISTINCT p.name) as produtos;
# Em qual ambiente está o produto Cloud Eye?
MATCH (p:Produto)-[:LOCALIZADO]->(f:LOCAL)
WHERE toLower(p.name) CONTAINS toLower("Cloud Eye")
RETURN collect(DISTINCT f.name) as local;
# Qual a diferença entre o preço do produto Oracle Cloud Infrastructure Compute Classic e Oracle Cloud Infrastructure Compute?
MATCH (p1:Produto)-[:VALOR_MENSAL_REAL_PRODUTO]->(v1:VALOR_MENSAL_REAL),
WHERE toLower(p1.name) CONTAINS toLower("Oracle Cloud Infrastructure Compute Classic") 
MATCH (p2:Produto)-[:VALOR_MENSAL_REAL_PRODUTO]->(v2:VALOR_MENSAL_REAL)
WHERE toLower(p2.name) CONTAINS toLower("Oracle Cloud Infrastructure Compute")
RETURN (toFloat(replace(v1.name,",",".")) - toFloat(replace(v2.name,",","."))) as diferenca 
# Quais plataformas possuem produtos de Logging Analytics?"
MATCH (p:Produto)-[:LOCALIZADO]->(f:LOCAL)
WHERE toLower(e.name) CONTAINS toLower("Logging Analytics")
RETURN f.name as plataforma
# Quantos produtos de analytics existem na plataforma DRCC?
MATCH (p:Produto)-[:LOCALIZADO]->(f:LOCAL)
WHERE toLower(f.name) CONTAINS toLower("DRCC") and toLower(p.name) CONTAINS toLower("analytics")
RETURN count(p) as total
# Quais produtos de storage estao disponiveis?
MATCH (p:Produto)-[:ESPECIFICADO_COMO]->(e:Especificacao)
MATCH (p:Produto)-[:LOCALIZADO]->(f:LOCAL)
WHERE toLower(e.name) CONTAINS toLower("storage")
RETURN p.name as produto, f.name as plataforma

Note: Do not include any explanations or apologies in your responses.
Do not respond to any questions that might ask anything else than for you to construct a Cypher statement.
Do not include any text except the generated Cypher statement.

The question is:
{question}"""
CYPHER_GENERATION_PROMPT = PromptTemplate(
    input_variables=["question", "schema"], template=CYPHER_GENERATION_TEMPLATE
)

#### LANGSMITH #######

os.environ['LANGCHAIN_TRACING_V2'] = os.getenv("LANGCHAIN_TRACING_V2")
os.environ['LANGCHAIN_ENDPOINT'] = os.getenv("LANGCHAIN_ENDPOINT")
os.environ['LANGCHAIN_API_KEY'] = os.getenv("LANGCHAIN_API_KEY")
os.environ['LANGCHAIN_PROJECT'] = os.getenv("LANGCHAIN_PROJECT_CONTEXTO")

######################


os.environ['OPENAI_API_KEY'] = os.getenv("OPENAI_API_KEY")
os.environ["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_KEY")
llm = ChatAnthropic(
    model="claude-3-5-sonnet-20240620",
    temperature=0,
    max_tokens=1024,
    timeout=None,
    max_retries=2,
    # other params...
)
graph = Neo4jGraph(
    url=os.getenv("NEO4J_URL"), 
    username=os.getenv("NEO4J_USERNAME"), 
    password=os.getenv("NEO4J_PASSWORD"))

chain_language_example = GraphCypherQAChain.from_llm(
    ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo"), graph=graph, 
    verbose=True,
    allow_dangerous_requests = True,
    cypher_prompt=CYPHER_GENERATION_PROMPT,
)

@traceable
def generate_response(input_text):
    # Run the chain with the required input variable
    graph.refresh_schema()
    result = chain_language_example.run(query=input_text)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Você é um assistente que vai utilizar a resposta encontrada para formular uma frase e responder ao usuário com base no contexto da pergunta. A resposta da pergunta do usuário está a seguir. Resposta: {result}.",
            ),
            ("human", "{input_text}"),
        ]
    )

    chain = prompt | llm

    response = chain.invoke(
        {
            "input_text": input_text,
            "result": result
        }
    )
    st.info(response.content)  # Output the final message


with st.form("my_form"):
    text = st.text_area("Enter text:", "Qual a especificacao do produto Oracle Autonomous JSON Database-ECPU?")
    submitted = st.form_submit_button("Submit")
    if submitted:
        generate_response(text)  # Call the function to generate a response
        

