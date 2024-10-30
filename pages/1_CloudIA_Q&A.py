import streamlit as st
import anthropic
import os 
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate



load_dotenv()

os.environ["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_KEY")

llm = ChatAnthropic(
    model="claude-3-5-sonnet-20240620",
    temperature=0,
    max_tokens=1024,
    timeout=None,
    max_retries=2,
    # other params...
)

st.title("📝 CloudIA - Q&A")
uploaded_file = st.file_uploader("Faça o upload de arquivo TXT ou MD e faça perguntas diretamente pelo Chat.", type=("txt", "md"))
question = st.text_input(
    "Ask something about the article",
    placeholder="Can you give me a short summary?",
    disabled=not uploaded_file,
)


if uploaded_file and question :
    article = uploaded_file.read().decode()

    prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful assistant that understands the following article: to {article}.",
        ),
        ("human", "{question}"),
    ]
)

    chain = prompt | llm

    response = chain.invoke(
        {
            "article": article,
            "question": question
        }
    )

    st.write("### Answer")
    st.write(response.content)
