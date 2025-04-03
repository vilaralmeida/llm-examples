from openai import OpenAI
import streamlit as st
from streamlit_feedback import streamlit_feedback
import pika
import json

with st.sidebar:
    openai_api_key = st.text_input("OpenAI API Key", key="feedback_api_key", type="password")
    "[Get an OpenAI API key](https://platform.openai.com/account/api-keys)"
    "[View the source code](https://github.com/streamlit/llm-examples/blob/main/pages/5_Chat_with_user_feedback.py)"
    "[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/streamlit/llm-examples?quickstart=1)"

st.title("📝 Chat with feedback (Trubrics)")

"""
In this example, we're using [streamlit-feedback](https://github.com/trubrics/streamlit-feedback) and Trubrics to collect and store feedback
from the user about the LLM responses.
"""

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "How can I help you? Leave feedback to help me improve!"}
    ]
if "response" not in st.session_state:
    st.session_state["response"] = None

messages = st.session_state.messages
for msg in messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input(placeholder="Tell me a joke about sharks"):
    messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    if not openai_api_key:
        st.info("Please add your OpenAI API key to continue.")
        st.stop()
    client = OpenAI(api_key=openai_api_key)
    response = client.chat.completions.create(model="gpt-3.5-turbo", messages=messages)
    st.session_state["response"] = response.choices[0].message.content
    with st.chat_message("assistant"):
        messages.append({"role": "assistant", "content": st.session_state["response"]})
        st.write(st.session_state["response"])

if st.session_state["response"]:
    feedback = streamlit_feedback(
        feedback_type="thumbs",
        optional_text_label="[Optional] Please provide an explanation",
        key=f"feedback_{len(messages)}",
    )
    # This app is logging feedback to Trubrics backend, but you can send it anywhere.
    # The return value of streamlit_feedback() is just a dict.
    # Configure your own account at https://trubrics.streamlit.app/
    if feedback and "rabbitmq_user" in st.secrets:

        message = {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "age": 30
        }

        # Convert the message to a JSON string
        message_json = json.dumps(message)

        credentials = pika.PlainCredentials(st.secrets.rabbitmq_user, st.secrets.rabbitmq_user_password)
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost', credentials=credentials))
        channel = connection.channel()
        # Declare a queue
        channel.queue_declare(queue='SUIATasks2')

        # Publish the JSON message to the queue
        channel.basic_publish(exchange='',
                            routing_key='SUIATasks2',
                            body=message_json)

        connection.close()

        # config = trubrics.init(
        #     email=st.secrets.TRUBRICS_EMAIL,
        #     password=st.secrets.TRUBRICS_PASSWORD,
        # )
        # collection = trubrics.collect(
        #     component_name="default",
        #     model="gpt",
        #     response=feedback,
        #     metadata={"chat": messages},
        # )
        # trubrics.save(config, collection)
        st.toast("Feedback recorded!", icon="📝")
