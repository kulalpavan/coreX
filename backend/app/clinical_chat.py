from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from typing import Any

from .guardrail import guardrail

CHAT_DISCLAIMER = "This assistant explains information found in the uploaded report. It is not a diagnosis or medical advice. Consult a licensed clinician for personal decisions."

SYSTEM_PROMPT = """You are a helpful medical assistant that explains laboratory reports to patients in plain language.
You have access to the raw text of their report, as well as the structured, confirmed results.

STRICT MEDICAL GUARDRAILS:
1. DO NOT diagnose conditions, suggest diseases, or predict outcomes.
2. DO NOT recommend treatments, medications, or lifestyle changes.
3. DO NOT state whether something is an emergency or dangerous.
4. If a user asks a diagnostic or treatment question, politely refuse and advise them to consult their clinician.
5. Base all your answers strictly on the provided report context. Do not invent values or tests that are not present.
6. Keep your answers concise, clear, and empathetic.
"""

def answer_question(question: str, history: list[Any], report: dict[str, Any]) -> dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"answer": "The chatbot is currently offline. Please configure GEMINI_API_KEY to enable AI chat.", "disclaimer": CHAT_DISCLAIMER, "refused": True}
        
    question = question.strip()
    if not question:
        return {"answer": "Please ask a question.", "disclaimer": CHAT_DISCLAIMER}

    # Format the report context
    context = "=== REPORT CONTEXT ===\n"
    if "raw_text" in report:
        context += f"Raw OCR Text:\n{report['raw_text']}\n\n"
    if "results" in report:
        context += "Confirmed Structured Results:\n"
        for r in report["results"]:
            context += f"- {r.get('raw_test_name')}: {r.get('value')} {r.get('unit')} (Range: {r.get('reference_range_low')} - {r.get('reference_range_high')}, Flag: {r.get('flag')})\n"
    context += "======================\n\n"

    # Build contents for Gemini API
    contents = []
    
    # Inject context into the first user message if history is empty, else put it in a separate user message at start
    first_msg_text = context + "Please answer my questions based on the report above."
    contents.append({"role": "user", "parts": [{"text": first_msg_text}]})
    contents.append({"role": "model", "parts": [{"text": "I understand. I will answer your questions based only on the provided report, and I will not provide medical diagnosis or treatment advice."}]})
    
    for msg in history:
        # Pydantic objects or dicts
        role = msg.role if hasattr(msg, "role") else msg.get("role")
        content = msg.content if hasattr(msg, "content") else msg.get("content")
        gemini_role = "user" if role == "user" else "model"
        contents.append({"role": gemini_role, "parts": [{"text": content}]})
        
    contents.append({"role": "user", "parts": [{"text": question}]})
    
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.2}
    }
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
    
    try:
        response = urllib.request.urlopen(req, timeout=20.0)
        data = json.loads(response.read().decode("utf-8"))
        answer = data["candidates"][0]["content"]["parts"][0]["text"]
        refused = any(
            kw in answer.lower()
            for kw in ["cannot diagnose", "cannot prescribe", "consult your clinician", "consult a licensed clinician", "refuse"]
        ) or ("safe" in answer.lower() and "false" in answer.lower())
        return {"answer": answer, "disclaimer": CHAT_DISCLAIMER, "refused": refused}
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        return {"answer": f"API Error: {e.code} - {err_msg}", "disclaimer": CHAT_DISCLAIMER, "refused": True}
    except Exception as e:
        return {"answer": f"Error communicating with AI: {str(e)}", "disclaimer": CHAT_DISCLAIMER, "refused": True}
