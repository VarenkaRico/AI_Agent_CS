# AI Support Triage Agent MVP

This Streamlit app is a first-tier customer support tool using AI to:
- Classify customer email sentiment.
- Assess urgency.
- Engage users in a dynamic Q&A chat.
- Automatically schedule a 15-min Google Meet support session when frustration or urgency is detected.

---

## 💡 Features

- 🔍 **Sentiment & Urgency Detection** using Amazon Bedrock's Nova model.
- 🧠 **Dynamic Questioning** with memory using LangGraph.
- 📅 **Google Calendar Integration** for fallback call scheduling.
- 🧾 **Privacy Policy Awareness** via gated chat initiation.

---

## 🛠️ Setup

### Prerequisites
- Python 3.8+
- Google API credentials (`oauth_credentials.json`)
- `.env` file with AWS credentials

### Install dependencies

```bash
pip install -r requirements.txt
```
🚀 Run the App
```bash
streamlit run AI_FirstTier.py
```
📂 File Structure
| File              | Description                                                   |
| ----------------- | ------------------------------------------------------------- |
| `AI_FirstTier.py` | Entry point for analyzing incoming emails                     |
| `agent_chat.py`   | Interactive Streamlit chat agent                              |
| `backend.py`      | AI logic: prompts, Bedrock calls, sentiment/urgency detection |
| `f_calendar.py`   | Google Calendar integration and availability detection        |

🔐 Authentication
Ensure you have:

Google OAuth credentials in oauth_credentials.json

AWS credentials via .env or environment variables