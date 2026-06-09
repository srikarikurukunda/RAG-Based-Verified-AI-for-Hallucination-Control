from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """
You are a precise, factual assistant.
Answer ONLY using the provided context. Do not use outside knowledge.
If the context does not contain the answer, say: "I cannot find this in the knowledge base."

When answering, you MUST follow this exact format:

REASONING:
Step 1: [first logical step]
Step 2: [second logical step]
Step 3: [continue as needed]

FINAL ANSWER:
[Your concise, factual answer here]

Do NOT skip the REASONING section.
Do NOT speculate. If you are unsure, say so explicitly.
"""

def get_ai_response(question: str, context: str) -> dict:
    prompt = SYSTEM_PROMPT + "\n\nCONTEXT:\n" + context + "\n\nQuestion: " + question
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    raw = response.choices[0].message.content
    return parse_response(raw)

def parse_response(raw: str) -> dict:
    reasoning, final_answer = '', ''
    if 'REASONING:' in raw and 'FINAL ANSWER:' in raw:
        parts = raw.split('FINAL ANSWER:')
        reasoning = parts[0].replace('REASONING:', '').strip()
        final_answer = parts[1].strip()
    return {'reasoning': reasoning, 'answer': final_answer, 'raw': raw}