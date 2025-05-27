import streamlit as st
import json
import urllib.parse
from datetime import datetime, timedelta, timezone
from utils.backend import classify_sentiment, invoke_nova, start_chat, generate_next_question
from utils.f_calendar import create_calendar_event
from langchain_core.runnables import RunnableLambda
from langgraph.graph import StateGraph
from typing import TypedDict, Union
from langchain.prompts import PromptTemplate

# Initialize
if "question_counter" not in st.session_state:
    st.session_state.update({
        "question_counter": 0,
        "interactions": [],
        "frustration_detected": False,
        "finished": False
    })

# Load from query params
query_params = st.query_params
client_email = urllib.parse.unquote(query_params.get("email", ["{}"]))
email_text = urllib.parse.unquote(query_params.get("email_text", [""]))
summary_data = json.loads(urllib.parse.unquote(query_params.get("summary_data", ["{}"])))

st.title("AI Support Chat Agent")
st.markdown(f"**Client Email:** {client_email}")
st.markdown(f"**Issue Summary:** {summary_data.get('summary', 'Not available')}")

# Chat
if st.session_state["question_counter"] == 0:
    result = start_chat(email_text, summary_data.get('questions', {}))
    initial_q = result["interaction"]["Q1"]["question_asked"]
    st.session_state.interactions.append({"question": initial_q, 
                                         "answer": "",
                                         "sentiment": ""
                                        })
    st.session_state.question_counter += 1

#Show latest unanswered question
latest = st.session_state.interactions[-1]
user_input = st.text_input(f"Q{st.session_state.question_counter}: {latest['question']}", 
                           key = "chat_input")

if st.button("Submit Answer"):
    if user_input.strip():
        sentiment_data = classify_sentiment(user_input)
        sentiment = sentiment_data.get("sentiment_identified", "Neutral")

        #Save answer
        latest["answer"] = user_input
        latest["sentiment"] = sentiment

        interactions = st.session_state.interactions

        # Assess Sentiment
        if sentiment in ["Frustrated", "Angry"]:
            st.session_state.frustration_detected = True
            st.session_state.finished = True
            st.warning("Thank you for your answers. A meeting will be scheduled with one of our technical teams")
            urgency = {
                "email_text": email_text,
                "reasoning": "Frustrated during chat conversation",
                "urgency_identified": "High_Chat"
                    }
            link = create_calendar_event(email_text, summary_data, urgency, st.session_state["interactions"])
            st.success("High priority issue detected. 15-min call scheduled.")
            st.markdown(f"[Join Google Meet]({link})")

        elif st.session_state.question_counter >= 10:
            st.session_state.finished = True
            st.success("Thank you for your responses. Our team will follow up.")
            urgency = {
                "email_text": email_text,
                "reasoning": "No more questions required",
                "urgency_identified": "Medium_Chat"
                    }
            link = create_calendar_event(email_text, summary_data, urgency, st.session_state["interactions"])
            st.success("High priority issue detected. 15-min call scheduled.")
            st.markdown(f"[Join Google Meet]({link})")

        else:
            combined_context = {
                "email": email_text,
                "questions": summary_data.get("questions", {}),
                "previous": st.session_state.interactions
            }

            # Next question
            next_prompt = generate_next_question(combined_context)
            st.session_state.interactions.append({"question": next_prompt, 
                                              "answer": "",
                                              "sentiment": ""})
        
            st.session_state.question_counter += 1
            st.experimental_rerun()