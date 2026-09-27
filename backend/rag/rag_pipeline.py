import os
from typing import List, Dict, Optional, Union
from backend.rag.vector_store import vector_store
from backend.ai.llm_client import llm_client


SYSTEM_RAG_PROMPT = (
    "You are MetroHealth AI Care Assistant, an intelligent, empathetic, and professional hospital customer care chatbot. "
    "Your objective is to help patients and visitors with accurate information, appointment guidelines, hospital policies, "
    "doctor schedules, billing inquiries, and complaint resolution in real-time.\n\n"
    "CRITICAL GUIDELINES:\n"
    "1. Conversational Style: Speak warmly, professionally, and naturally like an expert customer care agent (ChatGPT style). "
    "Use bullet points and bold headers to make medical/administrative details easy to read.\n"
    "2. Grounding: When Hospital Knowledge Base context is provided, ground your answers in those facts. "
    "Do NOT fabricate policies, timings, or prices.\n"
    "3. Patient Safety Boundary: You are a customer support agent, NOT a physician. "
    "Never diagnose medical conditions, never prescribe medications, and never alter dosages. "
    "If a patient describes an urgent medical symptom, direct them to emergency services immediately.\n"
    "4. Helpful Next Steps: Conclude your responses with a welcoming offer for further assistance."
)


def generate_rag_response(
    query: str,
    intent_info: dict,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    return_details: bool = False,
) -> Union[str, Dict[str, object]]:
    """
    Generates a real-time, grounded conversational response using:
      1. FAISS RAG Retrieval — searches top-3 relevant knowledge base documents.
      2. Real-Time LLM (Google Gemini / Groq / OpenAI) — synthesizes natural, grounded answers.
    """
    intent = intent_info.get("intent", "general_inquiry")
    category = intent_info.get("category", "information")
    department = intent_info.get("department", "Customer Support")

    # 1. Retrieve RAG domain context from FAISS
    context_text = ""
    try:
        context_docs = vector_store.search(query, top_k=3)
        if context_docs:
            context_text = "\n\n---\n\n".join([
                f"[Source: {d.get('source', 'Knowledge Base')}]\n{d.get('content', '')}"
                for d in context_docs
            ])
    except Exception as e:
        print(f"[RAG] FAISS retrieval error: {e}")

    if not context_text and intent != "greeting":
        response_text = "I couldn't find a verified answer in the hospital information available to me."
        if return_details:
            return {"message": response_text, "grounded": False}
        return response_text

    # 2. Build task-specific instructions
    custom_prompt = (
        f"{SYSTEM_RAG_PROMPT}\n\n"
        f"Context Details:\n"
        f"- Inferred Intent: {intent}\n"
        f"- Inquiry Category: {category}\n"
        f"- Responsible Department: {department}\n"
    )

    # 3. Generate response using RealTimeLLMClient
    response_text = llm_client.generate(
        user_message=query,
        system_prompt=custom_prompt,
        context_docs=context_text if context_text else None,
        conversation_history=conversation_history,
        temperature=0.3
    )

    if return_details:
        return {"message": response_text, "grounded": bool(context_text)}
    return response_text
