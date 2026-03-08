from backend.database import supabase


def save_message(session_id: str, role: str, message: str):
    supabase.table("conversations").insert({
        "session_id": session_id,
        "role": role,
        "message": message
    }).execute()


def get_conversation_history(session_id: str, limit: int = 8):
    result = (
        supabase.table("conversations")
        .select("*")
        .eq("session_id", session_id)
        .order("created_at")
        .execute()
    )

    rows = result.data[-limit:] if result.data else []

    history = []
    for row in rows:
        history.append({
            "role": row["role"],
            "content": row["message"]
        })

    return history