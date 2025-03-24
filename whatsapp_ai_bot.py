
from flask import Flask, request
import requests
import docx
from transformers import pipeline
from twilio.twiml.messaging_response import MessagingResponse
from bs4 import BeautifulSoup

app = Flask(__name__)

# AI Model for Answer Prediction
qa_model = pipeline("question-answering")

# WhatsApp API Configuration (Twilio Sandbox Number)
TWILIO_WHATSAPP_NUMBER = "whatsapp:+14155238886"

# Extract questions from a Word document
def extract_text_from_docx(docx_file):
    doc = docx.Document(docx_file)
    return [para.text for para in doc.paragraphs if para.text.strip()]

# Extract questions from a Google Form
def fetch_questions_from_google_form(form_url):
    response = requests.get(form_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    questions = [q.text for q in soup.find_all('div', class_='M7eMe')]
    return questions if questions else ["Unable to extract questions from the form."]

# Extract key questions (5-6 most important)
def extract_key_questions(questions, num_questions=6):
    return questions[:num_questions]

# Predict full answers based on key responses
def auto_fill_answers(questions, user_answers, full_questions):
    responses = {q: ans for q, ans in zip(questions, user_answers)}
    predicted_responses = {
        q: qa_model(question=q, context=" ".join(full_questions))['answer']
        for q in full_questions if q not in responses
    }
    responses.update(predicted_responses)
    return responses

# WhatsApp Webhook to receive messages
@app.route("/whatsapp", methods=["POST"])
def whatsapp_bot():
    incoming_msg = request.values.get("Body", "").lower()
    media_url = request.values.get("MediaUrl0", "")
    resp = MessagingResponse()

    # If user sends a Word doc
    if media_url.endswith(".docx"):
        doc_path = "received_questionnaire.docx"
        r = requests.get(media_url)
        with open(doc_path, "wb") as f:
            f.write(r.content)
        questions = extract_text_from_docx(doc_path)

    # If user sends a Google Form link
    elif "docs.google.com/forms" in incoming_msg:
        questions = fetch_questions_from_google_form(incoming_msg)

    else:
        resp.message("Please send a valid Word document or Google Form link.")
        return str(resp)

    # Extract & send key questions to the user
    key_questions = extract_key_questions(questions)
    resp.message("Please answer these questions:")
    for q in key_questions:
        resp.message(q)

    return str(resp)

if __name__ == "__main__":
    app.run(debug=True)
