import streamlit as st

from datetime import datetime, timedelta, timezone
import pickle
import os

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# GOOGLE CALENDAR
CALENDAR_ID = 'primary'
#st.set_page_config(page_title = 'AI Support Agent Simulator', layout = "centered")
#@st.cache_resource

def get_calendar_service():
    SERVICE_ACCOUNT_FILE = 'oauth_credentials.json'
    SCOPES = ['https://www.googleapis.com/auth/calendar']

    credentials = None
    token_path = "token.pkl"

    #---- For personal account use ----
    if os.path.exists(token_path):
        with open(token_path, "rb") as token:
            credentials = pickle.load(token)

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                SERVICE_ACCOUNT_FILE, SCOPES
                )
            
            credentials = flow.run_local_server(port=8765)

        with open(token_path, "wb") as token:
            pickle.dump(credentials, token)

    #---- For service accounts use -----
    #SCOPES = ['https://www.googleapis.com/auth/calendar']

    # credentials = service_account.Credentials.from_service_account_file(
    #     SERVICE_ACCOUNT_FILE, scopes = SCOPES
    # )

    return build('calendar', 'v3', credentials = credentials)

calendar_service = get_calendar_service()

def find_next_available_slot(duration_minutes = 15, search_hours = 2):
    now = datetime.now(timezone.utc)
    end_search = now + timedelta(hours = search_hours)
    check_start = now + timedelta(minutes = 5)

    body = {
        "timeMin": check_start.isoformat(),
        "timeMax": end_search.isoformat(),
        "timeZone": "UTC",
        "items":[{"id": "primary"}]
    }

    freebusy_result = calendar_service.freebusy().query(body = body).execute()
    busy_times = freebusy_result["calendars"]["primary"]["busy"]

    busy_sorted = sorted(busy_times, key=lambda b: b["start"])
    free_start = check_start

    for busy in busy_sorted:
        busy_start = datetime.fromisoformat(busy["start"].replace("Z","+00:00"))
        busy_end = datetime.fromisoformat(busy["end"].replace("Z","+00:00"))

        if free_start + timedelta(minutes=duration_minutes) <= busy_start:
            return free_start, free_start + timedelta(minutes=duration_minutes)
        
        if busy_end > free_start:
            free_start = busy_end

    # Check at the end of busy times
    if free_start + timedelta(minutes=duration_minutes) <= end_search:
        return free_start, free_start + timedelta(minutes=duration_minutes)

    return None, None #None available slot found

def create_calendar_event(client_email, summary, urgency = "Medium", interaction = None):

    urgency_level = urgency.get("urgency_identified")
    suggested_questions = summary.get("questions", "No questions provided") if isinstance(summary, dict) else str(summary)
    summary_text = summary.get("summary", "No summary provided") if isinstance(summary, dict) else str(summary)
    
    description_text = (f"{summary_text}."
        f"After analyzing the issue, AI agent suggests starting with these questions {suggested_questions}"
        f"Interaction in chat: {interaction}"
    )
    start_time, end_time = find_next_available_slot()

    if not start_time:
        return None

    event = {
        'summary': f"{urgency_level} - Support Call: {client_email}",
        'description': f"{description_text}",
        'start': {'dateTime': start_time.replace(microsecond=0).isoformat(),
                  'timeZone': 'UTC'},
        'end': {'dateTime': end_time.replace(microsecond=0).isoformat(),
                  'timeZone': 'UTC'}
        # when changing to Google Workspace domain
        #,'attendees': [{'email': client_email}],
    }
    import pprint
    pprint.pprint(event)
    created_event = calendar_service.events().insert(calendarId = CALENDAR_ID, body=event).execute()
    print(created_event.get('htmlLink'))
    return created_event.get('htmlLink')