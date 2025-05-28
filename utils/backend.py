import json
from langchain.prompts import PromptTemplate
#import boto3
from dotenv import load_dotenv
import re
import os
from openai import OpenAI
import streamlit as st

load_dotenv()

## AWS Sagemaker: NOVA

# bedrock = boto3.client(service_name="bedrock-runtime",
#                          region_name = "us-east-1")
# MODEL_ID = "amazon.nova-lite-v1:0"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL_OPEN_AI = "gpt-3.5-turbo"

def invoke_nova(prompt):

    body = json.dumps({
        "messages": [
            {
                "role": "user",
                "content": [
                    {"text": prompt}
                ]
            }
        ]
     }).encode("utf-8")

    try:
        response = bedrock.invoke_model(
            modelId=MODEL_ID,
            body=body,
            accept="application/json",
            contentType="application/json"
        )
        response_body = json.loads(response.get('body').read().decode('utf-8'))
        result = response_body["output"]["message"]["content"][0]["text"]

    except Exception as e:
         return f"Error: {e}"
    
    match = re.search(r'```(?:json)?\s*([\s\S])+?\s*```', result, re.DOTALL)

    if match:
        result = match.group(1)

    try:
        validation_result = json.loads(result)
    
    except json.JSONDecodeError:
        validation_result = {"email_text": "Unknown", "reasoning": "Model output could not be parsed"}

    return validation_result

def invoke_chatgpt(prompt):
    response = client.chat.completions.create(
    model=MODEL_OPEN_AI,
    messages=[{"role": "user", "content": prompt}]
    )  
    return response.choices[0].message.content

#USEFULE FUNCTIONS
def wrap_json_output(text):
    """Extract valid JSON from messy model output."""
    try:
        # Attempt to extract a clean JSON block from output
        match = re.search(r'{.*}', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        else:
            return json.loads(text)  # fallback
    except Exception as e:
        return {"error": f"JSON parsing failed: {e}", "raw": text}

# PROMPTS
prompt_sentiment = PromptTemplate.from_template(
    """
    You are an empathetic customer service agent. 
    Classify the following email sentiment as Neutral, Angry, Frustrated, or Stressed.
    Return the output as a raw JSON string without markdown formatting or triple backticks in the following structure:
     {{
        "email_text": {email},
        "reasoning": "Step-by-step reasoning for your conclusion",
        "sentiment_identified": "Neutral" | "Angry" | "Frustrated" | "Stressed"
        }}

    Email to Review:
        {email}
    """
)

prompt_issue_extraction = PromptTemplate.from_template(
    """
    You are a technical customer service agent. 
    Summarize the following email to help identify the main issue.
    Suggest 5 questions to get more information from the customer, so issue can be better identified.
    Return the output as raw JSON string without markdown formatting or triple backticks in the following structure:
     {{
        "email_text": {email},
        "summary": summary,
        "reasoning": "Step-by-step reasoning for your questions",
        "questions": [{{"Q1": question 1,
                        "Q2": question 2,
                        "Q3": question 3,
                        "Q4": question 4,
                        "Q5": question 5}}]
        }}

    Email to Review:
        {email}
    """
)

prompt_urgency = PromptTemplate.from_template(
    """
    You are a technical customer service agent. 
    Based on this email, how urgent is the issue? Respond with one of the following levels: Low, Medium, High, Critical.
    Return the output as raw JSON string without markdown formatting or triple backticks in the following structure:
     {{
        "email_text": {email},
        "reasoning": "Step-by-step reasoning for your conclusion",
        "urgency_identified": "Low" | "Medium" | "High" | "Critical"
        }}

    Email to Review:
        {email}
    """
)

prompt_greeting = PromptTemplate.from_template(
    """
    You are a sympathetic customer support agent who has been contacted with the client who has sent an email to the helpdesk.
    This is the email from the client {email}.
    You have also been provided with suggested clarification questions:
    {questions}
    Start the by providing the information that by proceding with the chat, she/he will accept the privacy policy (the user can find it at www.AI_first_tier.com/privacy_policy)
    
    Continue the conversation with a polite greeting and the first clarification question. You either can consider any of the questions provided before or ask a new one.
    The objective of this first question should be to clarify the issue presented.
    Only ask **one** question for now. Do not simulate the user's answer.
    Assess the answer and identify the sentiment.
    Return only the greeting and the first question in this format:

    {{
        "email_text": {email},
        "interaction": {{
            "Q1": {{"question_asked": "...", 
                "answer_received": "",
                "reasoning": "Step-by-step reasoning for asking this question",
                "sentiment_identified": ""
    }}

    Make sure you greet the customer and thank him/her for being our customer.
    """)

prompt_next_question = PromptTemplate.from_template(
    """
    You are a helpful AI support agent in a live conversation.
    You have received the following customer email:
    
    {email}

    Based on this email, you previously suggested some follow-up questions:
    {suggested_questions}

    Here is a summary of your previous interactions with the client:
    {interaction_history}

    Your task is to ask ONE new, meaningful, non-redundant question that can help the technical team understand and resolve the issue faster.

    Return only this JSON (do not include any markdown formattin or backticks):

    {{
        "question": "...",
        "reasoning": "Explain why this new question is useful given the history.
    }}
    """
)

#FUNCTIONS AGENT
   
def classify_sentiment(email):
    prompt = prompt_sentiment.format(email=email)
    #response = invoke_nova(prompt)
    response = invoke_chatgpt(prompt)
    return wrap_json_output(response)

def extract_issue_summary(email):
    prompt = prompt_issue_extraction.format(email=email)
    #response = invoke_nova(prompt)
    response = invoke_chatgpt(prompt)
    return wrap_json_output(response)


def detect_urgency(email):
    prompt = prompt_urgency.format(email=email)
    #response = invoke_nova(prompt)
    response = invoke_chatgpt(prompt)
    return wrap_json_output(response)


def start_chat(email, questions):
    prompt = prompt_greeting.format(email=email, questions=questions)
    #response = invoke_nova(prompt)
    response = invoke_chatgpt(prompt)
    return wrap_json_output(response)


def generate_next_question(context):
    email = context.get("email", "")
    suggested = context.get("questions", {})
    previous = context.get("previous", {})

    history_str = "\n".join([
        f"Q{i+1}: {qa['question']} | A: {qa['answer']} | Sentiment: {qa['sentiment']}"
        for i, qa in enumerate(previous)
    ])

    prompt = prompt_next_question.format(email=email, 
                                         suggested_questions=json.dumps(suggested),
                                         interaction_history = history_str
                                         )
    
    #response = invoke_nova(prompt)
    response = invoke_chatgpt(prompt)
    return wrap_json_output(response)


