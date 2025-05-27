import streamlit as st
import json
from datetime import datetime, timedelta, timezone
import urllib.parse
from typing import TypedDict
from utils.backend import classify_sentiment, start_chat, generate_next_question
from utils.f_calendar import create_calendar_event
from langgraph.graph import StateGraph
from langchain_core.runnables import RunnableLambda

# ==== Session Init ====
for key, default in {
    "question_counter": 0,
    "interactions": [],
    "frustration_detected": False,
    "finished": False,
    "chat_started": False,
    "privacy_accepted": False,
    "chat_input": "",
    "clear_input": False,
    "meeting_link": ""
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# === Privacy Acceptance ===
if not st.session_state["privacy_accepted"]:
    #st.title("AI Support Chat Agent")
    st.info("Before we begin, please accept our [Privacy Policy] (https://www.AI_first_tier.com/privacy_policy).")
    if st.button("Accept and Continue"):
        st.session_state["privacy_accepted"] = True

    else:
        st.stop()

# ==== Load Parameters ====
query_params = st.query_params
client_email = urllib.parse.unquote(query_params.get("email", ["{}"]))
email_text = urllib.parse.unquote(query_params.get("email_text", [""]))
summary_data = json.loads(urllib.parse.unquote(query_params.get("summary_data", ["{}"])))

st.title("AI Support Chat Agent")
st.markdown(f"**Client Email:** {client_email}")
st.markdown(f"**Issue Summary:** {summary_data.get('summary', 'Not available')}")

# ==== Define State ====
class ChatState(TypedDict):
    email: str
    summary: dict
    question_count: int
    interactions: list
    finished: bool
    frustration_detected: bool
    meeting_link: str

# ==== Nodes ====
def start_chat_node(state: ChatState) -> ChatState:
    #print(f"Start Chat at {datetime.now()}")
    if not state["interactions"]:
        result = start_chat(state["email"], state["summary"].get('questions', {}))
        first_q = result["interaction"]["Q1"]["question_asked"]
        state["interactions"].append({"question": first_q, "answer": "", "sentiment": ""})
        state["question_count"] += 1
    return state



def ask_next(state: ChatState) -> ChatState:
    if state["finished"] == False:
        print("ASK_NEXT")
        context = {
            "email": state["email"],
            "questions": state["summary"].get("questions", {}),
            "previous": state["interactions"]
        }
        q = generate_next_question(context)["question"]
        state["interactions"].append({"question": q, "answer": "", "sentiment": ""})
        state["question_count"] += 1
    return state

def wait_for_input(state: ChatState) -> ChatState:
    #print("WAIT")
    #Place holder to give control back to Streamlit
    return state

def record_response(state: ChatState) -> ChatState:
    #print("RECORD RESPONSE")
    user_input = st.session_state.get("chat_input", "").strip()
    if user_input and state["interactions"]: #and not state["interactions"][-1]["answer"]:
        for interaction in state["interactions"]:
            if interaction["answer"]== "":
                sentiment_data = classify_sentiment(user_input)
                sentiment = sentiment_data.get("sentiment_identified", "Neutral")
                interaction.update({
                    "answer": user_input,
                    "sentiment": sentiment
                })
                if sentiment in ["Frustrated", "Angry"]:
                    state["frustration_detected"] = True
                    state["finished"] = True
                break
    return state

def check_completion(state: ChatState) -> ChatState:
    print("CHECK COMPLETION")
    print(state["question_count"])
    print(state["frustration_detected"])
    if state["frustration_detected"]:
        print("Meeting because sentiment")
        state["__branch__"] = "schedule"
    elif state["question_count"] >= 10:
        print("Meeting because question counts")
        state["finished"] = True
        state["__branch__"] = "schedule"
    else:
        print("Continue")
        state["__branch__"] = "continue"
        print(state["__branch__"])
    return state

def schedule_meeting(state: ChatState) -> ChatState:

    print("SCHEDULE", state["frustration_detected"], state["finished"])
    if state["frustration_detected"] in ["Frustrated", "Angry"] or state["finished"] == True:
        urgency = {
            "email_text": state["email"],
            "reasoning": "Frustrated or completed all questions",
            "urgency_identified": "High_Chat" if state["frustration_detected"] else "Medium_Chat"
        }
        link = create_calendar_event(client_email, state["summary"], urgency, state["interactions"])
        state["meeting_link"] = link or ""
        state["finished"] = True
    return state

def end_chat(state: ChatState) -> ChatState:
    print("END")
    st.success("Thank you for your responses. Our team will follow up.")
    return state

# ==== Graph ====
graph = StateGraph(ChatState)

ask_node = RunnableLambda(ask_next)
record_node = RunnableLambda(record_response)
check_node = RunnableLambda(check_completion)
schedule_node = RunnableLambda(schedule_meeting)
end_node = RunnableLambda(end_chat)
wait_node = RunnableLambda(wait_for_input)

graph.add_node("ask_next", ask_node)
graph.add_node("wait_for_input", wait_node)
graph.add_node("record_response", record_node)
graph.add_node("check_completion", check_node)
graph.add_node("schedule_meeting", schedule_node)
graph.add_node("end_chat", end_node)

graph.set_entry_point("record_response")
#st.markdown("ENTRY POINT OK")

graph.add_edge("record_response", "check_completion")


graph.add_conditional_edges("check_completion", {
    "continue": ask_node,
    "schedule": schedule_node
})
#st.markdown("CONDITIONAL EDGE OK")
graph.add_edge("ask_next", "wait_for_input")
graph.add_edge("schedule_meeting", "end_chat")

#st.markdown("END OK")

app = graph.compile()

if not st.session_state.chat_started:
    

    init_state = ChatState(
        email=email_text,
        summary=summary_data,
        question_count=st.session_state["question_counter"],
        interactions=st.session_state["interactions"],
        finished=st.session_state["finished"],
        frustration_detected=st.session_state["frustration_detected"],
        meeting_link=""
    )
    
    updated_state = start_chat_node(init_state)

    st.session_state.update({
        "question_counter": updated_state["question_count"],
        "interactions": updated_state["interactions"],
        "frustration_detected": updated_state["frustration_detected"],
        "finished": updated_state["finished"],
        "chat_started": True,
        "meeting_link": updated_state["meeting_link"]
        })

    
    st.rerun()

# ==== CHAT ====

# Show latest question input
if not st.session_state.finished:
    if (
        st.session_state.interactions and 
        st.session_state.interactions[-1].get("answer", "") == ""
    ):
        latest = st.session_state.interactions[-1]
        if st.session_state.get("clear_input", False):
            if "chat_input" in st.session_state:
                del st.session_state["chat_input"]
            st.session_state["clear_input"] = False

        st.text_input(f"Q{st.session_state.question_counter-1}: {latest['question']}", key="chat_input")

    if st.button("Submit Answer"):

        state = ChatState(
            email=email_text,
            summary=summary_data,
            question_count=st.session_state["question_counter"],
            interactions=st.session_state["interactions"],
            finished=st.session_state["finished"],
            frustration_detected=st.session_state["frustration_detected"]
        )

        result = app.invoke(state)
        # Update Streamlit state
        st.session_state.update({
            "question_counter": state["question_count"],
            "interactions": state["interactions"],
            "frustration_detected": state["frustration_detected"],
            "finished": state["finished"],
            #"chat_input": "",
            "clear_input": True
        })
        st.rerun()

# Show meeting link if available


# Show chat history
st.markdown("### Chat History")
for i, item in enumerate(st.session_state.interactions):
    st.markdown(f"**Q{i+1}:** {item['question']}")
    st.markdown(f"**A:** {item['answer']}  \n*Sentiment:* {item['sentiment']}")

    if i == 10 or item['sentiment'] in ["Frustrated", "Angry"]:
        st.success("15-min call scheduled.")
        st.markdown(f"[Join Google Meet]({st.session_state['meeting_link']})")

