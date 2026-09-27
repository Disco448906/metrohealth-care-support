from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from backend.schemas.schemas import ChatMessageRequest, ChatMessageResponse
from backend.services.decision_engine import process_customer_query
from backend.database.connection import get_db
from backend.api.auth import get_current_user

router = APIRouter(prefix="/api/chat", tags=["Chatbot & AI Decision Engine"])


@router.post("", response_model=ChatMessageResponse)
def handle_chat(
    chat_req: ChatMessageRequest,
    current_user: dict = Depends(get_current_user)
):
    # -----------------------------------------------------------------------
    # Resolve authenticated user from JWT (or fall back to guest)
    # -----------------------------------------------------------------------
    if current_user.get("role") != "customer":
        raise HTTPException(status_code=403, detail="Patient chatbot access is for patient accounts.")
    user_id = str(current_user["id"])
    user_name = current_user.get("name", "Patient")

    # -----------------------------------------------------------------------
    # Validate message
    # -----------------------------------------------------------------------
    if not chat_req.message or not chat_req.message.strip():
        return ChatMessageResponse(
            message="Please provide a message query.",
            intent="invalid_empty",
            category="general",
            severity="LOW",
            priority="LOW",
            action="AUTO_RESOLVE",
            ticket_id=None,
            department="Customer Support",
            rag_used=False,
            confidence=0.0,
            method="validation"
        )

    db = get_db()

    # -----------------------------------------------------------------------
    # Resolve conversation_id — must be stable across turns
    # -----------------------------------------------------------------------
    conversation_id = (
        chat_req.conversation_id
        or f"conv_{user_id}_{int(datetime.utcnow().timestamp())}"
    )

    # -----------------------------------------------------------------------
    # Fetch last 4 messages from this conversation for multi-turn context
    # -----------------------------------------------------------------------
    history_cursor = db["chat_history"].find(
        {"conversation_id": conversation_id, "user_id": user_id},
        sort=[("created_at", -1)],
        limit=4
    )
    raw_history = list(history_cursor)
    # Reverse to chronological order and format for LLM
    conversation_history = []
    for turn in reversed(raw_history):
        conversation_history.append({"role": "user",      "content": turn.get("user_message", "")})
        conversation_history.append({"role": "assistant", "content": turn.get("ai_response", "")})

    # -----------------------------------------------------------------------
    # Process query through LLM decision engine
    # -----------------------------------------------------------------------
    response_data = process_customer_query(
        message=chat_req.message,
        user_id=user_id,
        user_name=user_name,
        conversation_id=conversation_id,
        conversation_history=conversation_history
    )

    # -----------------------------------------------------------------------
    # Persist chat turn to history
    # -----------------------------------------------------------------------
    try:
        db["chat_history"].insert_one({
            "user_id": user_id,
            "user_name": user_name,
            "conversation_id": conversation_id,
            "user_message": chat_req.message,
            "ai_response": response_data["message"],
            "intent": response_data["intent"],
            "category": response_data["category"],
            "severity": response_data["severity"],
            "action": response_data["action"],
            "ticket_id": response_data.get("ticket_id"),
            "confidence": response_data.get("confidence"),
            "method": response_data.get("method"),
            "created_at": datetime.utcnow().isoformat()
        })
    except Exception as e:
        print(f"[Chat] Warning: failed to save chat history: {e}")

    return ChatMessageResponse(**response_data)


@router.get("/status")
def get_chat_status():
    """Returns active real-time LLM status and RAG index health."""
    from backend.ai.llm_client import llm_client
    from backend.rag.vector_store import vector_store
    return {
        "active_provider": llm_client.active_provider,
        "is_configured": llm_client.is_configured(),
        "rag_ready": vector_store.is_initialized,
        "rag_chunks_count": len(vector_store.documents) if vector_store.documents else 0
    }

@router.get("/history")
def get_chat_history(conversation_id: str, current_user: dict = Depends(get_current_user)):
    """Return recent turns only when they belong to the signed-in patient."""
    if current_user.get("role") != "customer":
        raise HTTPException(status_code=403, detail="Patient chatbot access is for patient accounts.")
    db = get_db()
    turns = db["chat_history"].find(
        {"conversation_id": conversation_id, "user_id": str(current_user["id"])},
        {"_id": 0, "user_message": 1, "ai_response": 1, "intent": 1, "category": 1, "severity": 1, "action": 1, "ticket_id": 1, "department": 1, "created_at": 1},
    ).sort("created_at", 1).limit(30)
    return list(turns)
