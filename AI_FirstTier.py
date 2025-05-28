import streamlit as st
#import boto3
from dotenv import load_dotenv
import os
import uuid
import urllib.parse
import json
from datetime import datetime, timedelta, timezone
#from botocore.exceptions import NoCredentialsError


import sys

# Add the root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), '..')))
from utils.backend import classify_sentiment, extract_issue_summary, detect_urgency
from utils.f_calendar import create_calendar_event

load_dotenv()

# FRONTEND
st.set_page_config(page_title = 'AI Support Agent Simulator', layout = "centered")
st.title("AI Support Triage Agent")

email_text = st.text_area("Paste Client Email")
client_email = st.text_input("Client Email")

if st.button("Analyze and Route"):
    sentiment = classify_sentiment(email_text)
    summary = extract_issue_summary(email_text)
    urgency = detect_urgency(email_text)

    st.write(f"**Sentiment:** {sentiment}")
    st.write(f"**Urgency:** {urgency}")
    st.write(f"**Issue Summary:** {summary}")

    if sentiment["sentiment_identified"] in ["Angry", "Frustrated"] or urgency["urgency_identified"] in ["High", "Critical"]:
        link = create_calendar_event(email_text, summary, urgency)
        st.success("High priority issue detected. 15-min call scheduled.")
        st.markdown(f"[Join Google Meet]({link})")
    else:
        encoded_summary = urllib.parse.quote(json.dumps(summary))
        encoded_email_text = urllib.parse.quote(email_text)
        chat_link = f"/agent_chat?session_id={uuid.uuid4()}&email={client_email}&email_text={encoded_email_text}&summary_data={encoded_summary}"
        st.info("Client invited to clarify issue in chat")
        st.markdown(f"[Continue to Chat Agent]({chat_link})")
