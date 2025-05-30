import streamlit as st
import os
import boto3
from botocore.client import Config
import pika
import json
import time
import re
from dotenv import load_dotenv
from py2neo import Graph

load_dotenv()

@st.fragment()
def getFatos(autor, documento):
    NEO4J_URI = st.secrets.NEO4J_URI
    NEO4J_USER = st.secrets.NEO4J_USER
    NEO4J_PASSWORD = st.secrets.NEO4J_PASSWORD
    # Connect to the Neo4j database
    graph = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    query = f"""
        MATCH (a:AtomicFact)<-[:HAS_ATOMIC_FACT]-(c:Chunk)<-[:HAS_CHUNK]-(d:Document)
        WHERE d.autor = \"{autor}\" and d.id = \"{documento}\"
        RETURN DISTINCT a.text as fato
    """
    
    results = graph.run(query)
    
    retorno = []
    
    for fatos in results:
        retorno.append(fatos["fato"])

    return retorno

@st.fragment()
def getPersonagens(autor, documento):
    NEO4J_URI = st.secrets.NEO4J_URI
    NEO4J_USER = st.secrets.NEO4J_USER
    NEO4J_PASSWORD = st.secrets.NEO4J_PASSWORD
    # Connect to the Neo4j database
    graph = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    query = f"""
        MATCH (k:Character)<-[:Character]-(a:AtomicFact)<-[:HAS_ATOMIC_FACT]-(c:Chunk)<-[:HAS_CHUNK]-(d:Document)
        WHERE d.autor = \"{autor}\" and d.id = \"{documento}\"
        RETURN DISTINCT k.text as character
    """
    
    results = graph.run(query)
    
    retorno = []
    
    for character in results:
        retorno.append(character["character"])

    return retorno

def verificaDocumento(documento, autor):
    NEO4J_URI = st.secrets.NEO4J_URI
    NEO4J_USER = st.secrets.NEO4J_USER
    NEO4J_PASSWORD = st.secrets.NEO4J_PASSWORD
    # Connect to the Neo4j database
    graph = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))    
    query = f"""
            MATCH (d:Document)
            WHERE d.autor = "{autor}" AND d.id = "{documento}"
            RETURN COUNT(d) > 0 AS documentExists
    """
    result = graph.run(query)
    record = result.evaluate()    
    
    return record

# True se tiver que retornar narrativas com mais de um personagem. Por padrão, Falso.    
def listaDocumentos(autor, maisUmPersonagem = False):
    NEO4J_URI = st.secrets.NEO4J_URI
    NEO4J_USER = st.secrets.NEO4J_USER
    NEO4J_PASSWORD = st.secrets.NEO4J_PASSWORD
    # Connect to the Neo4j database
    graph = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))    
    query = ""
    

    if (maisUmPersonagem):
        query = f"""
            MATCH (k:Character)<-[:Character]-(a:AtomicFact)<-[:HAS_ATOMIC_FACT]-(c:Chunk)<-[:HAS_CHUNK]-(d:Document)
            WHERE d.autor = \"{autor}\" and d.contexto = 'NOVA_NARRATIVA'
            WITH d.id AS conteudo, COUNT(DISTINCT k) AS characterCount
            WHERE characterCount > 1
            RETURN conteudo
        """
    else:
        query = f"""
            MATCH (d:Document)
            WHERE d.autor = \"{autor}\" and d.contexto = 'NOVA_NARRATIVA'
            RETURN DISTINCT d.id as conteudo
        """
    
    
    results = graph.run(query)
    
    retorno = []
    
    for x in results:
        retorno.append(x["conteudo"])

    return retorno   


@st.fragment()
def sanitize_string(input_string):
    # Define the regex pattern
    pattern = r'^[a-zA-Z0-9.\-_]{1,255}$'
    
    # Check if the string matches the regex
    if re.match(pattern, input_string):
        return input_string  # String is already valid
    
    # Sanitize the string: remove invalid characters
    sanitized = re.sub(r'[^a-zA-Z0-9.\-_]', '', input_string)
    
    # Truncate to 255 characters if necessary
    return sanitized[:255]

@st.fragment()
def updateFile(filename, usuario, content):
    # st.write(content)
    session = boto3.session.Session()
    client = session.client('s3',
                        endpoint_url=st.secrets.BUCKET_ENDPOINT,
                        config=Config(s3={'addressing_style': 'virtual'}), 
                        region_name=st.secrets.BUCKET_REGION_NAME, 
                        aws_access_key_id=st.secrets.BUCKET_ACCESS_ID, 
                        aws_secret_access_key=st.secrets.BUCKET_ACCESS_KEY) 


    userspace = sanitize_string(usuario)
    path = userspace + "/" + filename

    isCreated = False
    r = client.list_objects(Bucket=st.secrets.BUCKET_NAME)
    if  r.get('Contents') is not None:   
        for n in r.get('Contents'):
            if path in n['Key']:
                isCreated = True
                break
    
    # Create a new Space.
    if not isCreated:
        client.put_object(Bucket=st.secrets.BUCKET_NAME, 
                    Key=path, # Object key, referenced whenever you want to access this file later.
                    Body=content, # The object's contents.
                    ACL='private', # Defines Access-control List (ACL) permissions, such as private or public.
                    Metadata={ # Defines metadata tags.
                        'user': usuario                      
                    }
                    )
        
@st.fragment()
def solicitaCargaBaseConhecimento(document_name, AUTOR, CONTEXTO, IDIOMA, PERSONA):
    
    message = {
        "DOCUMENT_NAME": document_name,
        "AUTOR": AUTOR,
        "CONTEXTO": CONTEXTO,
        "IDIOMA": IDIOMA,
        "PERSONA": PERSONA        
    }
    # Convert the message to a JSON string
    message_json = json.dumps(message)

    credentials = pika.PlainCredentials(st.secrets.rabbitmq_user, st.secrets.rabbitmq_user_password)
    connection = pika.BlockingConnection(pika.ConnectionParameters(st.secrets.rabbitmq_server, credentials=credentials))
    channel = connection.channel()
    # Declare a queue
    channel.queue_declare(queue=st.secrets.QUEUE_KNOWLEDGE_DB)

    # Publish the JSON message to the queue
    channel.basic_publish(exchange='',
                        routing_key=st.secrets.QUEUE_KNOWLEDGE_DB,
                        body=message_json)
    connection.close()
        
        
def carrega_fatos(documento, personagem, autor) -> str:
    fatos = ""
    NEO4J_URI = st.secrets.NEO4J_URI
    NEO4J_USER = st.secrets.NEO4J_USER
    NEO4J_PASSWORD = st.secrets.NEO4J_PASSWORD

    graph = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))        

    # Fatos Atomicos mais relevantes para um personagem especifico
    qry_Relevant_Facts_About_Character = f"""
        MATCH (c:Character)
        WHERE c.text = \"{personagem}\"
        WITH c
        MATCH (a:AtomicFact)
        WHERE (a)-[:Character]->(c)
        WITH a
        MATCH (k:Chunk)
        WHERE (k)-[:HAS_ATOMIC_FACT]->(a)
        WITH k,a
        MATCH (d:Document)
        WHERE (d)-[:HAS_CHUNK]->(k) and d.id = \"{documento}\" and d.autor = \"{autor}\"
        RETURN a.text as texto
    """    

    results = graph.run(qry_Relevant_Facts_About_Character)
        # Process and print the results
    for record in results:    
        texto = record["texto"]        
        fatos += f"Fato: {texto}\n"
    
    return fatos


instrucoes = """
Você é um ajudante na jornada de um escritor em melhorar a escrita de seu conteúdo.

O conteúdo escrito por ele é: {nova_historia}

O tom das sugestões deve estar alinhado com o estilo geral da história, seja ele esperançoso, trágico, misterioso ou aberto.

IMPORTANT: SOMENTE O TEXTO DEVE SER A SAÍDA! NÃO INCLUIR QUALQUER REFERENCIA AS DECISÕES TOMADAS, SOBRE OS PARAMETROS DE ENTRADA E QUALQUER OUTRA INFORMAÇÃO QUE NÃO SEJA ESTRITAMENTE SOBRE A HISTÓRIA!!!

Após o título coloque um ponto final.

NA RESPOSTA NÃO UTILIZAR \\n para quebra de linha.

IMPORTANTE: O RESULTADO DEVE SER ESCRITO NO IDIOMA: {IDIOMA}

"""


PROMPT_PERSONAGEM = """

PRECISO QUE ME DÊ {COUNT} IDÉIAS DE COMO AVANÇAR COM A ESCRITA DO MEU LIVRO/CONTO. 

O FOCO DA SUGESTAO DEVE SER NO PERSONAGEM: {PERSONAGEM}.


PARA CADA UMA DAS {COUNT} IDEIAS, CONSIDERE:

################################
CONSIDERE A SEGUINTE ABORDAGEM ESTRUTURAL PARA CONDUZIR A PROPOSTA DE IDEIAS/SUGESTÕES PARA EVOLUIR A NARRATIVA:

{STRUCTURE}

################################
CONSIDERE O SEGUINTE RECURSO NARRATIVO PARA CONDUZIR A PROPOSTA DE IDEIAS/SUGESTÕES DA NARRATIVA:
{RECURSO}

################################
A NARRATIVA RESUMIDA ESTÁ A SEGUIR

{NARRATIVE}

################################
FATOS MAIS RELEVANTES QUE DEVEM SER CONSIDERADOS NA SUA SUGESTÃO:

{FACTS}

O tom das sugestões deve estar alinhado com o estilo geral da história, seja ele esperançoso, trágico, misterioso ou aberto.


Ao final, apresente ao usuário as seguintes informações por tópicos:


IMPORTANTE: MANTER REFERENCIA A NARRATIVA E A PERSONAGEM NA PROPOSTA GERADA!!

- Titulo: Um titulo que resume a ideia proposta.
- Proposta: Ideia que deverá evoluir com base na NARRATIVA, na PERSONAGEM, estrutura e recurso narrativo sugerido pelo usuário. 
- Personagem: Como a ideia impacta a jornada do personagem?
- De que forma a ideia está relacionada à abordagem estrutural proposta? (Ex.: A alternância emocional é alcançada através das indecisões do personagem .....)
- De que forma o recurso narrativo foi abordado? (ex.: incluí a Alegoria ao sugerir que o amor fosse representado através da relação entre o algodão e a desfiadeira....)
- Como a proposta sugerida evita que o escritor caia no lugar comum em relação a seu conteúdo? 

IMPORTANTE: O RESULTADO DEVE SER ESCRITO NO IDIOMA: {IDIOMA}

"""

PROMPT_FATO = """

PRECISO QUE ME DÊ {COUNT} IDÉIAS DE COMO AVANÇAR COM A ESCRITA DO MEU LIVRO/CONTO. 

O FOCO DA SUGESTAO DEVE SER NO FATO: {FATO}.


PARA CADA UMA DAS {COUNT} IDEIAS, CONSIDERE:

################################
CONSIDERE A SEGUINTE ABORDAGEM ESTRUTURAL PARA CONDUZIR A PROPOSTA DE IDEIAS/SUGESTÕES PARA EVOLUIR A NARRATIVA:

{STRUCTURE}

################################
CONSIDERE O SEGUINTE RECURSO NARRATIVO PARA CONDUZIR A PROPOSTA DE IDEIAS/SUGESTÕES DA NARRATIVA:
{RECURSO}

################################
A NARRATIVA RESUMIDA ESTÁ A SEGUIR

{NARRATIVE}

################################
FATOS MAIS RELEVANTES QUE DEVEM SER CONSIDERADOS NA SUA SUGESTÃO:

{FACTS}

O tom das sugestões deve estar alinhado com o estilo geral da história, seja ele esperançoso, trágico, misterioso ou aberto.


Ao final, apresente ao usuário as seguintes informações por tópicos:


IMPORTANTE: MANTER REFERENCIA A NARRATIVA E A PERSONAGEM NA PROPOSTA GERADA!!

- Titulo: Um titulo que resume a ideia proposta.
- Proposta: Ideia que deverá evoluir com base na NARRATIVA, na PERSONAGEM, estrutura e recurso narrativo sugerido pelo usuário. 
- Personagem: Como a ideia impacta a jornada do personagem?
- De que forma a ideia está relacionada à abordagem estrutural proposta? (Ex.: A alternância emocional é alcançada através das indecisões do personagem .....)
- De que forma o recurso narrativo foi abordado? (ex.: incluí a Alegoria ao sugerir que o amor fosse representado através da relação entre o algodão e a desfiadeira....)
- Como a proposta sugerida evita que o escritor caia no lugar comum em relação a seu conteúdo? 

IMPORTANTE: O RESULTADO DEVE SER ESCRITO NO IDIOMA: {IDIOMA}



"""


def get_instrucoes(nova_historia, idioma):
    return instrucoes.format(
        nova_historia = nova_historia,
        IDIOMA=idioma
    )       

def digitaPrompt(texto):
    for word in texto.split(" "):
        yield word + " "
        time.sleep(0.02)  

@staticmethod
def get_prompt_fato(count, narrativa, fato, structure, facts, recurso, idioma):
    return PROMPT_FATO.format(
        COUNT=count,
        NARRATIVE=narrativa,
        FATO=fato,
        STRUCTURE=structure,
        FACTS=facts,
        RECURSO=recurso,
        IDIOMA=idioma
    )

@staticmethod
def get_prompt_personagem(count, personagem, narrativa, structure, facts, recurso, idioma):
    return PROMPT_PERSONAGEM.format(
        COUNT=count,
        PERSONAGEM=personagem.upper(),
        NARRATIVE=narrativa.upper(),
        STRUCTURE=structure.upper(),
        FACTS=facts.upper(),
        RECURSO=recurso.upper(),
        IDIOMA=idioma.upper()
    )

       
estruturas = ["LINHA DO TEMPO", "ALTERNÂNCIA EMOCIONAL","LEAD", "O HOMEM NO BURACO", "DOS TRAPOS À RIQUEZA", "SOLUÇÃO ERRADA"]

tamanho_texto = ["Muito Pequeno", "Pequeno", "Medio", "Grande"]


def getTamanhoTexto():
    return tamanho_texto

def getEstruturas():
    return estruturas


def getRecursos():
    return recursos


STRUCTURE_1 = """

LINHA DO TEMPO: A NARRATIVA IRÁ SE DESENROLAR EM TORNO DE UMA LINHA DO TEMPO. A SEQUENCIA NARRATIVA DEVE SER TEMPORAL, CONSIDERANDO QUE OS EVENTOS OCORREM EM UMA ORDEM CRONOLÓGICA. 

"""

STRUCTURE_2 = """

ALTERNÂNCIA EMOCIONAL: A NARRATIVA TORNA-SE UMA JORNADA EMOCIONAL. DESSA FORMA, AO ALTERNAR EMOÇÕES POSITIVAS E NEGATIVAS, O ENREDO AVANÇA: UMA DERROTA DÁ LUGAR A UMA VITÓRIA; UM ALÍVIO CÔMICO QUEBRA UM MOMENTO DE TENSÃO.

"""


STRUCTURE_3 = """

LEAD: A O COMEÇO TORNA-SE A PARTE MAIS IMPORTANTE DA NARRATIVA. LOGO NO COMEÇO CRIAM-SE CURIOSIDADES, INTRIGA-SE OS LEITORES OU AINDA SUGERE-SE O QUE ESTÁ POR VIR. 

"""

STRUCTURE_4 = """

O HOMEM NO BURACO: A NARRATIVA COMEÇA EM UM LUGAR POSITIVO (ZONA DE CONFORTO) PARA LOGO EM SEGUIDA UM PROBLEMA INESPERADO OCORRER (GATILHO). A CRISE SE INSTAURA, CAUSANDO MEDO, AFLIÇÃO, RAIVA OU DESESPERO. MAS LOGO É POSSÍVEL ENCONTRAR UMA SOLUÇÃO OU UM CAMINHO. POR FIM, MOSTRA-SE QUE O MOMENTO DIFÍCIL FOI PASSAGEIRO E QUE O FIM DA NARRATIVA É EM UM LUGAR MELHOR.

"""


STRUCTURE_5 = """

DOS TRAPOS À RIQUEZA: AQUI A NARRATIVA SE INICIA COM UM VALOR OCULTO, ONDE ALGO É VISTO COMO NEGATIVO (uma habilidade, uma emoção, um pensamento, um objeto, etc...), entretanto percebe-se que isso pode ser um erro. O elemento negativo é colocado à prova (ASCENÇÃO) e, para a surpresa do leitor, ele se mostra como algo extremamente valioso.

"""

STRUCTURE_6 = """

SOLUÇÃO ERRADA: A NARRATIVA COMEÇA EM UM LUGAR NEGATIVO, E UMA PRIMEIRA SOLUÇÃO PARECER SER CORRETA. ENTRETANTO, ELA SE MOSTRA FALHA (REVÉS) e a situação é agravada. APÓS ENCONTRAR A RECUPERAÇÃO, A SOLUÇÃO VERDADEIRA É ENCONTRADA. Por fim, aprendemos a tomar melhores decisões. 

"""

STRUCTURE_DEFAULT = """

NÃO É NECESSÁRIO ADOTAR UMA ESTRUTURA PREDEFINIDA. 

"""

RECURSO_DEFAULT = """

NÃO É NECESSÁRIO ADOTAR UM RECURSO

"""


recursos = ["ALEGORIA", "ALIVIO COMICO", "CONTEXTO", "COMPARAÇÃO", "CONTRASTE", "CURIOSIDADE", "DADOS VALIDADORES", "DISCORDÂNCIA",
            "GANCHO", "IDENTIFICAÇÃO", "INTERAÇÃO", "METALINGUAGEM", "MISTÉRIO", "NÚMERO MÁGICO", "PERSONIFICAÇÃO", "PLOT TWIST",
            "PONTO DE VISTA","PRENÚNCIO", "QUEBRA DE PADRÃO", "RELATO", "REVELAÇÃO", "SURPRESA", "TEMPO", "VITÓRIA RÁPIDA", "VIDA PREGRESSA",
            "ANTAGONISMO", "ANEDOTA","ALUSÃO"]

RECURSO_1 = """
ALEGORIA: Representar. Figurar. Simular. Descreva um cenário ou enredo ficcional que claramente remeta à realidade da narrativa. 
"""
RECURSO_2 = """
ALÍVIO CÔMICO: Brincar. Divertir. Fruir. Faça uma observação espirituosa, quebre a quarta parede ou conte uma piada. 
"""
RECURSO_3 = """
CONTEXTO: Situar. Explicar. Conectar. Faça uma contextualização que seja útil, explorando as perguntas: Quem? O quê? Onde? Como? Por quê?
"""
RECURSO_4 = """
COMPARAÇÃO: Comparar. Simbolizar. Imaginar. Encontre a comparação capaz de fazer a explicação avançar com velocidade, seja por metáfora, analogia, e que explore um 
elemento mais simples que já se encontra no imaginário coletivo. 
"""
RECURSO_5 = """
CONTRASTE: Contrastar. Divergir. Diferenciar. O antes e o depois, o que é e o que não é, a mentira e a verdade, isso e aquilo. Encontre elementos que se contrapõem
no intuito de reforçar um argumento. 
"""
RECURSO_6 = """
CURIOSIDADE: Questionar. Instigar. Esconder. Faça uma pergunta engenhosa ou sugeria possuir uma informação que o outro desconheça. Qual a resposta? O que virá a seguir?
"""
RECURSO_7 = """
DADOS VALIDADORES: Comprovar. Concluir. Espantar. Utilize um número que é essencial para reforçar um ponto ou que cause espanto. Preserve a credibilidade apoiando-se 
em fontes confiáveis.
"""
RECURSO_8 = """
DISCORDÂNCIA: Divergir. Contrariar. Opor. Pondere sobre a questão e exponha sua discordância, ajudando a enxergar um outro ponto de vista.
"""
RECURSO_9 = """
GANCHO: Instigar. Entusiasmar. Amarrar. Nos últimos instantes, deixe uma pergunta em aberto ou introduza uma informação inédita à narrativa, prometendo conclusões em uma próxima
criação. 
"""
RECURSO_10 = """
IDENTIFICAÇÃO: Retratar. Conectar. Traduzir. Desperte o interesse ao apontar como o assunto do enredo se conecta de uma forma ou outra com crenças, comportamentos ou com 
a jornada da narrativa.
"""

RECURSO_11 = """
INTERAÇÃO: Motivar. Convocar. Desafiar. Abra espaço para participação ou peça opinião. Especificidade e clareza em relação ao que se espera é importante para 
aumentar a percepção de valor do leitor. 
"""
RECURSO_12 = """
METALINGUAGEM: Referenciar. Analisar. Explicar. Tente ser conciso e claro, sem abrir mão da praticidade. Explore a metalinguagem para fazer sua narrativa autorreferente. 
"""
RECURSO_13 = """
MISTÉRIO: Investigar. Insinuar. Cadenciar. Caminhe no sentido de uma investigação, cadenciando as informações conforme avança. Vez ou outra insinue o que está por vir.
"""
RECURSO_14 = """
NÚMERO MÁGICO: Facilitar. Listar. Adequar. Apresente um numero que pode ser referenciado em vários contextos para que os leitores possam lembrar com facilidade o que foi comunicado.
"""

RECURSO_15 = """
PERSONIFICAÇÃO: Fantasiar. Atribuir. Adjetivar. Dê um adjetivo inventivo ao assunto. Caso julgue pertinente, pode antropomorfizar a narrativa. 
"""

RECURSO_16 = """
PLOT TWIST: Mudar. Transformar. Surpreender. Próximo ao fim, uma reviravolta modifica o enredo. Por algum tempo, conduza a narrativa em uma direção. Então, subverta a 
expectativa trocando o dispositivo temático ou apresentação de uma informação que dá outro sentido a tudo que foi dito antes.
"""
RECURSO_17 = """
PONTO DE VISTA: Distinguir. Narrar. Representar. Use a primeira pessoa (eu) para transmitir pessoalidade e intimismo, a segunda pessoa (você) para transformar o leitor 
em participante ativo do enredo, ou a terceira pessoa (ele/ela) para dar a sensação de distância e neutralidade.
"""

RECURSO_18 = """
PRENÚNCIO: Sugerir. Insinuar. Apontar. Faça uma promessa ou sugestão que indique o que acontece no final, de forma a cativar o interesse do leitor no desfecho da narrativa. 
"""

RECURSO_19 = """
QUEBRA DE PADRÃO: Diferenciar. Subverter. Modificar. Seja um estilo, um discurso, ou um ponto de vista, não hesite em desconstruí-los. 
"""

RECURSO_20 = """
RELATO: Apresentar. Descrever. Divulgar. Relate passagens selecionadas na vida de figuras ilustres ou bons conhecidos capazes de ilustrar com perfeição o ponto da narrativa.
"""

RECURSO_21 = """
REVELAÇÃO: Revelar. Declarar. Exibir. Há uma revelação que é necessária ser feita. Após construir o mistério ou a curiosidade, deixe o leitor satisfeito fechando o ciclo
que foi aberto através de uma revelação. 
"""

RECURSO_22 = """
SURPRESA: Supreender. Impressionar. Cativar. Apresente uma informação inesperada, faça uma conexão improvável ou introduza um novo elemento à narrativa. 
"""


RECURSO_23 = """
Vitória Rápida: Facilitar. Instrumentalizar. Resumir. Ofereça utilidades práticas em forma de resumo, instruções ou orientações em passos que ajude o leitor a 
superar sua provações.
"""
RECURSO_24 = """
Vida Pregressa: Contar. Descrever. Contextualizar. Utilize elementos do passado da jornada como exemplo, pontuando um aprendizado, uma queda ou uma conquista que
reforçe a narrativa.
"""

RECURSO_25 = """
ANTAGONISMO: Expor. Combater. Derrotar. Ideias, crenças, desejos, sentimentos, pessoas, ou uma mistura disso tudo podem ser escalados ao papel de antagonista no enredo
proposto.
"""

RECURSO_26 = """
ANEDOTA: Recortar. Evidenciar. Distinguir. Seja um fato curioso, um acontecimento que faz rir ou repleto de significado, utilize-o. 
"""

RECURSO_27 = """
ALUSÃO: Referenciar. Adaptar. Relacionar. Referencie os clássicos, os modismos, as tendências ou as obras de nicho para cativar o leitor.
"""

RECURSO_28 = """
TEMPO: Retornar. Relembrar. Especular. Volte ao passado remoto em busca de elementos há muito esquecidos ou ao passado recente para despertar a nostalgia.
"""


def get_structure_prompt(estrutura) -> str:
    saida = ""
    if estrutura == estruturas[0]:
        saida = STRUCTURE_1
    elif estrutura == estruturas[1]:
        saida = STRUCTURE_2
    elif estrutura == estruturas[2]:
        saida = STRUCTURE_3
    elif estrutura == estruturas[3]:
        saida = STRUCTURE_4
    elif estrutura == estruturas[4]:
        saida = STRUCTURE_5
    elif estrutura == estruturas[5]:
        saida = STRUCTURE_6
        
    return saida    


def get_recurso_narrativo(recurso) -> str:
    saida = ""
    if recurso == recursos[0]:
        saida = RECURSO_1
    elif recurso == recursos[1]:
        saida = RECURSO_2
    elif recurso == recursos[2]:
        saida = RECURSO_3
    elif recurso == recursos[3]:
        saida = RECURSO_4
    elif recurso == recursos[4]:
        saida = RECURSO_5
    elif recurso == recursos[5]:
        saida = RECURSO_6
    elif recurso == recursos[6]:
        saida = RECURSO_7                        
    elif recurso == recursos[7]:
        saida = RECURSO_8
    elif recurso == recursos[8]:
        saida = RECURSO_9
    elif recurso == recursos[9]:
        saida = RECURSO_10
    elif recurso == recursos[10]:
        saida = RECURSO_11
    elif recurso == recursos[11]:
        saida = RECURSO_12
    elif recurso == recursos[12]:
        saida = RECURSO_13
    elif recurso == recursos[13]:
        saida = RECURSO_14
    elif recurso == recursos[14]:
        saida = RECURSO_15
    elif recurso == recursos[15]:
        saida = RECURSO_16
    elif recurso == recursos[16]:
        saida = RECURSO_17
    elif recurso == recursos[17]:
        saida = RECURSO_18
    elif recurso == recursos[18]:
        saida = RECURSO_19
    elif recurso == recursos[19]:
        saida = RECURSO_20
    elif recurso == recursos[20]:
        saida = RECURSO_21
    elif recurso == recursos[21]:
        saida = RECURSO_22
    elif recurso == recursos[22]:
        saida = RECURSO_23
    elif recurso == recursos[23]:
        saida = RECURSO_24
    elif recurso == recursos[24]:
        saida = RECURSO_25
    elif recurso == recursos[25]:
        saida = RECURSO_26
    elif recurso == recursos[26]:
        saida = RECURSO_27        
    elif recurso == recursos[27]:
        saida = RECURSO_28                                                                                                                                                                    
    return saida    
