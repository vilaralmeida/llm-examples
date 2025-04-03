# https://langchain-ai.github.io/langgraph/#example

from typing import Annotated, Literal, TypedDict
from pymongo import MongoClient
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_openai import OpenAIEmbeddings
from langchain_core.messages import HumanMessage
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph, MessagesState
from langgraph.prebuilt import ToolNode
from langsmith import traceable
import os
from dotenv import load_dotenv
from langchain.tools.retriever import create_retriever_tool
import streamlit as st

st.title("🔎 CloudIA - Conhecimento")
load_dotenv()
#### LANGSMITH #######

os.environ['LANGCHAIN_TRACING_V2'] = os.getenv("LANGCHAIN_TRACING_V2")
os.environ['LANGCHAIN_ENDPOINT'] = os.getenv("LANGCHAIN_ENDPOINT")
os.environ['LANGCHAIN_API_KEY'] = os.getenv("LANGCHAIN_API_KEY")
os.environ['LANGCHAIN_PROJECT'] = os.getenv("LANGCHAIN_PROJECT_CONHECIMENTO")

######################


os.environ['ANTHROPIC_API_KEY'] = os.getenv("ANTHROPIC_KEY")
client = MongoClient(os.getenv("MONGO_URI"))
dbName = os.getenv("MONGO_DB")
collectionName = os.getenv("MONGO_COLLECTION")
collection = client[dbName][collectionName]
INDEX = os.getenv("MONGO_INDEX")
embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
vectorStore = MongoDBAtlasVectorSearch(
    collection=collection,
    embedding=embeddings,
    index_name=INDEX,
)
retriever = vectorStore.as_retriever(top_k=1)
retriever_tool = create_retriever_tool(
    retriever,
    "retrieve_mongodb",
    "Search and return information stored on MongoDB.",
)
tools = [retriever_tool]
tool_node = ToolNode(tools)
model = ChatAnthropic(model="claude-3-5-sonnet-20240620", temperature=0).bind_tools(tools)


"""
Esse chat acessa uma base de conhecimento armazenada em um banco de dados de Vetor. Atualmente 
conta com arquivos compartilhados durante a composição da oferta de Multinuvem Oracle e Huawei.
"""
@traceable
def generate_response(input_text):
    # Define a new graph
    workflow = StateGraph(MessagesState)

    # Define the two nodes we will cycle between
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)

    # Set the entrypoint as `agent`
    # This means that this node is the first one called
    workflow.add_edge(START, "agent")

    # We now add a conditional edge
    workflow.add_conditional_edges(
        # First, we define the start node. We use `agent`.
        # This means these are the edges taken after the `agent` node is called.
        "agent",
        # Next, we pass in the function that will determine which node is called next.
        should_continue,
    )

    # We now add a normal edge from `tools` to `agent`.
    # This means that after `tools` is called, `agent` node is called next.
    workflow.add_edge("tools", 'agent')

    # Initialize memory to persist state between graph runs
    checkpointer = MemorySaver()

    # Finally, we compile it!
    # This compiles it into a LangChain Runnable,
    # meaning you can use it as you would any other runnable.
    # Note that we're (optionally) passing the memory when compiling the graph
    app = workflow.compile(checkpointer=checkpointer)

    # Use the Runnable
    final_state = app.invoke(
        {"messages": [HumanMessage(content=input_text)]},
        config={"configurable": {"thread_id": 42}}
    )
    st.info(final_state["messages"][-1].content)  # Output the final message

# Define the function that determines whether to continue or not
def should_continue(state: MessagesState) -> Literal["tools", END]:
    messages = state['messages']
    last_message = messages[-1]
    # If the LLM makes a tool call, then we route to the "tools" node
    if last_message.tool_calls:
        return "tools"
    # Otherwise, we stop (reply to the user)
    return END

# Define the function that calls the model
def call_model(state: MessagesState):
    messages = state['messages']
    response = model.invoke(messages)
    # We return a list, because this will get added to the existing list
    return {"messages": [response]}

with st.form("my_form"):
    text = st.text_area("Enter text:", "Quais são os produtos de storage ofertados?")
    submitted = st.form_submit_button("Submit")
    if submitted:
        generate_response(text)  # Call the function to generate a response
        

