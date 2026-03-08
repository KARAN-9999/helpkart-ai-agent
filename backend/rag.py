from backend.database import supabase
from backend.embeddings import create_embedding


def load_knowledge_base():
    with open("knowledge/helpkart_docs.txt", "r", encoding="utf-8") as f:
        docs = [doc.strip() for doc in f.read().split("\n\n") if doc.strip()]

    for doc in docs:
        embedding = create_embedding(doc)

        supabase.table("knowledge_base").insert({
            "content": doc,
            "embedding": embedding
        }).execute()

        print("Inserted:", doc[:80])


def retrieve_context(query: str, top_k: int = 3):
    query_embedding = create_embedding(query)

    result = supabase.rpc(
        "match_documents",
        {
            "query_embedding": query_embedding,
            "match_count": top_k
        }
    ).execute()

    return result.data if result.data else []


def format_context(query: str, top_k: int = 3) -> str:
    docs = retrieve_context(query, top_k=top_k)

    if not docs:
        return "No relevant knowledge found."

    # Fallback guard: if best similarity is too low, treat as missing context
    best_similarity = docs[0].get("similarity", 0)
    if best_similarity < 0.30:
        return "No relevant knowledge found."

    blocks = []
    for i, doc in enumerate(docs, start=1):
        blocks.append(f"[Context {i}]\n{doc['content']}")

    return "\n\n".join(blocks)


if __name__ == "__main__":
    load_knowledge_base()