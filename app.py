import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pypdf import PdfReader
import gradio as gr
from crewai import LLM, Agent, Task, Crew, Process
from crewai.tools import tool
from getpass import getpass
from dotenv import load_dotenv

load_dotenv()



# Email credentials (use env vars in real projects for safety!)
gmail_user = os.getenv("GMAIL_USER")
gmail_app_password = os.getenv("GMAIL_APP_PASSWORD")
notification_email = os.getenv("NOTIFICATION_EMAIL")


# Define Tools - Send Email Tool
@tool
def send_email_tool(subject:str,message:str)-> str:
    """
    Sends an email using Gmail SMTP server with the specified subject and message.

    Args:
        subject (str): The email subject line.
        message (str): The body message of the email.

    Returns:
        str: Status message indicating success or failure.
    """
    if not all([gmail_user, gmail_app_password, notification_email]):
        return "Email credentials are not set properly."
    
    try:
        msg = MIMEMultipart() # Creates a multipart email(can handle attachments etc..)
        msg['From'] = gmail_user
        msg['To'] = notification_email
        msg['Subject'] = subject
        msg.attach(MIMEText(message, 'plain')) #Attaches the message body as plain text to the email
        
        # Connect to Gmail SMTP Server and Send Email
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls() # Upgrade the connection to a secure encrypted SSL/TLS connection
        server.login(gmail_user, gmail_app_password)
        server.sendmail(gmail_user, notification_email, msg.as_string())
        server.quit()
        return "Email sent successfully!"
    except Exception as e:
        return f"Failed to send email: {str(e)}"

# PDF Parsing Utility Function
def parse_pdf(file_path : str) -> str:
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
           page_text = page.extract_text()
           if page_text:
               text += page_text + "\n"
        return text if text else "No text found in PDF."
    except Exception as e:
        return f"Error reading PDF: {str(e)}"

#  load LinkedIn Profile & Summary
linkedin = parse_pdf("files/SUDARKODI S - RESUME.pdf")

summary = ""
with open("files/summary.txt","r",encoding="utf-8") as f:
    summary = f.read()

name = "Sudarkodi S"

system_prompt = f"""You are {name}. Speak in first person.
Be natural and conversational and human-like — like you’re personally chatting with someone on your site.
Answer questions honestly based on the information available about your career, background, and skills.

## About You:
{linkedin} and {summary}
"""

# Define the Career Agent
career_agent = Agent(
    role = f"{name} - Career Representative",
    goal = f"Represent {name} professionally , help visitors with their queries regarding my career, background, skills, and experiences and capture leads",
    backstory=system_prompt,
    verbose=False,
    tools=[send_email_tool],
    llm = LLM(
        model="azure/gpt-4o",
        base_url=os.getenv("AZURE_API_BASE"),
        api_key=os.getenv("AZURE_API_KEY"),
        api_version="2024-12-01-preview"
    ),
    memory = True,
)


# Chat Function
def chat(message, history):
    context = ""
    for msg in history:
        if msg["role"] == "user":
            context += f"User: {msg['content']}\n"
        elif msg["role"] == "assistant":
            context += f"Assistant: {msg['content']}\n"
    
    task = Task(
    description=f"""
    Current user message :{message}
    Respond naturally as yourself, {name}.
    
     IMPORTANT TOOL USAGE:
        - Try to encourage users to share their email if they seem interested in connecting or hiring or to be in any kind of getting in touch
        - If user shares their email or wants to connect → use Send Email tool with subject 'New Contact: <Name>' and message including name, email, and summary of whole conversation.
        - If you cannot answer a question → use Send Email tool with subject 'Unanswered Question' and message including the exact user question and a short summary of whole conversation.
        - Do not expose tool calls to the user, just answer naturally.
      
    """,
    agent=career_agent,
    expected_output=f"A short , natural first-person reply from {name}."
)
    crew = Crew(
    agents=[career_agent],
    tasks=[task],
    verbose=True,
    tracing=False
)
    try:
        result = crew.kickoff()
        return getattr(result,'raw',str(result))
    except Exception as e:
        return f"Error: {str(e)}"

# ui using gradio
demo = gr.ChatInterface(
    chat,
    type="messages",
    title=f"Know more about {name}",
    description="Ask me anything about my career, background, skills, and experiences.",
    examples=[
        "Tell me about your experience",
        "What are your key skills?",
        "What projects have you worked on?",
        "What are your career goals?",
    ]
)

if __name__ == "__main__":
    demo.launch()  