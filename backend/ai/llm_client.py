import os
import json
import requests
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv

load_dotenv()


class RealTimeLLMClient:
    """
    Unified Real-Time LLM Client.
    Supports Google Gemini (Primary), Groq Cloud, OpenAI, and Hugging Face Router.
    Enables conversational, ChatGPT-style healthcare interactions with strict grounding.
    """

    DEFAULT_SYSTEM_PROMPT = (
        "You are MetroHealth AI Assistant, a compassionate, professional, and knowledgeable hospital customer care chatbot. "
        "Your mission is to assist patients and visitors with inquiries, appointment booking/rescheduling, "
        "hospital policies, doctor schedules, lab report guidance, and complaint resolution.\n\n"
        "GUIDING PRINCIPLES:\n"
        "1. Real-Time Conversational Style: Respond naturally, warmly, and empathetically like ChatGPT.\n"
        "2. Domain Grounding: When Hospital Knowledge Base context is provided, ground your answer strictly in that verified information.\n"
        "3. Medical Safety: You are a customer-care assistant, NOT a medical doctor. Do NOT diagnose diseases, prescribe medications, or alter clinical dosages.\n"
        "4. Clarity & Formatting: Use clear paragraphs, bullet points, and bold text for readability."
    )

    def __init__(self):
        self.reload_keys()

    def reload_keys(self):
        load_dotenv(override=True)
        self.gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
        self.groq_key = os.getenv("GROQ_API_KEY") or ""
        self.openai_key = os.getenv("OPENAI_API_KEY") or ""
        self.hf_token = os.getenv("HF_TOKEN") or ""

    @property
    def active_provider(self) -> str:
        self.reload_keys()
        if self.gemini_key and self.gemini_key not in ("YOUR_GEMINI_API_KEY", ""):
            return "Gemini (gemini-2.5-flash)"
        if self.groq_key and self.groq_key not in ("YOUR_GROQ_API_KEY", ""):
            return "Groq (llama-3.3-70b)"
        if self.openai_key and self.openai_key not in ("YOUR_OPENAI_API_KEY", ""):
            return "OpenAI (gpt-4o-mini)"
        if self.hf_token and len(self.hf_token) > 10 and not self.hf_token.startswith("YOUR_"):
            return "HuggingFace Router"
        return "Standby (Waiting for GEMINI_API_KEY in backend/.env)"

    def is_configured(self) -> bool:
        self.reload_keys()
        return bool(
            (self.gemini_key and self.gemini_key not in ("YOUR_GEMINI_API_KEY", "")) or
            (self.groq_key and self.groq_key not in ("YOUR_GROQ_API_KEY", "")) or
            (self.openai_key and self.openai_key not in ("YOUR_OPENAI_API_KEY", ""))
        )

    def generate(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        context_docs: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.4,
        max_tokens: int = 800
    ) -> str:
        """
        Generate a conversational response using the best available real-time LLM.
        """
        self.reload_keys()
        sys_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT

        # Inject RAG context if present
        if context_docs and context_docs.strip():
            sys_prompt += (
                f"\n\n--- VERIFIED HOSPITAL KNOWLEDGE BASE CONTEXT ---\n"
                f"{context_docs.strip()}\n"
                f"--- END CONTEXT ---\n"
                f"Please synthesize a clear, helpful response based on the verified knowledge base above. "
                f"If the answer is not contained in the context, inform the user honestly and offer to connect them with the appropriate department."
            )

        # 1. Try Google Gemini
        if self.gemini_key and self.gemini_key not in ("YOUR_GEMINI_API_KEY", ""):
            gemini_resp = self._call_gemini(
                user_message=user_message,
                system_prompt=sys_prompt,
                conversation_history=conversation_history,
                temperature=temperature,
                max_tokens=max_tokens
            )
            if gemini_resp:
                return gemini_resp

        # 2. Try Groq Cloud (Ultra-fast LLaMA 3.3)
        if self.groq_key and self.groq_key not in ("YOUR_GROQ_API_KEY", ""):
            groq_resp = self._call_groq(
                user_message=user_message,
                system_prompt=sys_prompt,
                conversation_history=conversation_history,
                temperature=temperature,
                max_tokens=max_tokens
            )
            if groq_resp:
                return groq_resp

        # 3. Try OpenAI
        if self.openai_key and self.openai_key not in ("YOUR_OPENAI_API_KEY", ""):
            openai_resp = self._call_openai(
                user_message=user_message,
                system_prompt=sys_prompt,
                conversation_history=conversation_history,
                temperature=temperature,
                max_tokens=max_tokens
            )
            if openai_resp:
                return openai_resp

        # 4. Fallback: Intelligent conversational synthesiser if API key pending
        return self._fallback_conversational_response(
            user_message=user_message,
            context_docs=context_docs,
            conversation_history=conversation_history
        )

    # -------------------------------------------------------------------------
    # Provider Implementations
    # -------------------------------------------------------------------------

    def _call_gemini(
        self,
        user_message: str,
        system_prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.4,
        max_tokens: int = 800
    ) -> Optional[str]:
        """
        Calls Google Gemini API (gemini-1.5-flash / gemini-2.0-flash) via REST.
        """
        for model in ["gemini-flash-latest", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3.5-flash"]:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.gemini_key}"
            
            contents = []
            if conversation_history:
                for turn in conversation_history[-6:]:
                    role = "user" if turn.get("role") == "user" else "model"
                    content = turn.get("content", "").strip()
                    if content:
                        contents.append({
                            "role": role,
                            "parts": [{"text": content}]
                        })

            contents.append({
                "role": "user",
                "parts": [{"text": user_message}]
            })

            payload = {
                "contents": contents,
                "systemInstruction": {
                    "parts": [{"text": system_prompt}]
                },
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                    "topP": 0.95
                }
            }

            try:
                res = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=20)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            ans = parts[0].get("text", "").strip()
                            if ans:
                                print(f"[LLM] Gemini ({model}) generated {len(ans)} chars successfully.")
                                return ans
                else:
                    print(f"[LLM] Gemini API error ({model}) {res.status_code}: {res.text[:200]}")
            except Exception as e:
                print(f"[LLM] Gemini API request exception ({model}): {e}")

        return None

    def _call_groq(
        self,
        user_message: str,
        system_prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.4,
        max_tokens: int = 800
    ) -> Optional[str]:
        """
        Calls Groq Cloud API (llama-3.3-70b-versatile).
        """
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.groq_key}",
            "Content-Type": "application/json"
        }

        messages = [{"role": "system", "content": system_prompt}]
        if conversation_history:
            for turn in conversation_history[-6:]:
                role = turn.get("role", "user")
                content = turn.get("content", "")
                if content:
                    messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": user_message})

        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        try:
            res = requests.post(url, json=payload, headers=headers, timeout=20)
            if res.status_code == 200:
                data = res.json()
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "").strip()
            else:
                print(f"[LLM] Groq error {res.status_code}: {res.text[:200]}")
        except Exception as e:
            print(f"[LLM] Groq request exception: {e}")

        return None

    def _call_openai(
        self,
        user_message: str,
        system_prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.4,
        max_tokens: int = 800
    ) -> Optional[str]:
        """
        Calls OpenAI API (gpt-4o-mini).
        """
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json"
        }

        messages = [{"role": "system", "content": system_prompt}]
        if conversation_history:
            for turn in conversation_history[-6:]:
                role = turn.get("role", "user")
                content = turn.get("content", "")
                if content:
                    messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": user_message})

        payload = {
            "model": "gpt-4o-mini",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        try:
            res = requests.post(url, json=payload, headers=headers, timeout=20)
            if res.status_code == 200:
                data = res.json()
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "").strip()
        except Exception as e:
            print(f"[LLM] OpenAI request exception: {e}")

        return None

    def _fallback_conversational_response(
        self,
        user_message: str,
        context_docs: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Provide a safe, user-facing fallback when a verified answer is unavailable.
        """
        msg_lower = user_message.lower().strip()

        # Handle greetings naturally
        if any(g in msg_lower for g in ["hi", "hello", "hey", "good morning", "good evening", "greetings"]):
            return (
                "Hello! Welcome to MetroHealth Customer Care. 😊\n\n"
                "I am your AI Healthcare Assistant. I can help you with:\n"
                "• **Hospital Timings & OPD Hours**\n"
                "• **Doctor Schedules & Appointments**\n"
                "• **Billing & Refund Queries**\n"
                "• **Lab Reports & Diagnostic Services**\n"
                "• **Raising and Tracking Support Tickets**\n\n"
                "How can I assist you today?"
            )

        # Handle RAG-grounded domain questions
        if context_docs and context_docs.strip():
            lines = [
                line.strip()
                for line in context_docs.split("\n")
                if line.strip() and not line.startswith("#") and not line.startswith("[Source:")
                   and not line.startswith("---")
            ]
            summary = "\n".join(lines[:6])
            return (
                f"Based on MetroHealth's official records:\n\n"
                f"{summary}\n\n"
                f"Is there anything specific you would like me to clarify or assist you with?"
            )

        # Do not expose deployment configuration or invent a hospital policy answer.
        return (
            f"I understand your query: *\"{user_message}\"*\n\n"
            f"I couldn't find a verified answer in the information available to me. You can check your patient hub "
            f"for appointments, reports, prescriptions, and bills, or tell me what went wrong and I can route it "
            f"to the appropriate support team."
        )


# Singleton LLM client instance
llm_client = RealTimeLLMClient()
