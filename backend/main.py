from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
from openai import OpenAI
import os
import uuid

from backend.memory import save_message, get_conversation_history
from backend.rag import format_context

load_dotenv(dotenv_path=".env", override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is missing in .env")

client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI()


@app.get("/")
def health_check():
    return {"status": "ok", "service": "HelpKart AI Support Agent"}


@app.websocket("/chat")
async def chat(websocket: WebSocket):
    await websocket.accept()
    session_id = str(uuid.uuid4())

    try:
        while True:
            user_message = await websocket.receive_text()
            save_message(session_id, "user", user_message)

            try:
                history = get_conversation_history(session_id)
                context = format_context(user_message, top_k=3)

                messages = [
                    {
                        "role": "system",
                        "content": (
                            "You are HelpKart AI Support Agent. "
                            "Answer like a professional customer support agent. "
                            "Use the retrieved context as the primary source of truth. "
                            "If the answer is not available in the context, clearly say you do not have enough information. "
                            "Do not hallucinate policies or order details."
                        ),
                    },
                    {
                        "role": "system",
                        "content": f"Retrieved context:\n\n{context}",
                    },
                ]

                messages.extend(history)

                stream = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    stream=True
                )

                full_reply = ""

                for chunk in stream:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        full_reply += delta
                        await websocket.send_text(delta)

                save_message(session_id, "assistant", full_reply)

            except Exception as e:
                error_message = (
                    "Sorry, I’m having trouble retrieving or generating a response right now. "
                    "Please try again in a moment."
                )
                print("Error during retrieval/generation:", str(e))
                save_message(session_id, "assistant", error_message)
                await websocket.send_text(error_message)

    except WebSocketDisconnect:
        print(f"Client disconnected. Session ended: {session_id}")