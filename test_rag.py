from backend.rag import retrieve_context

questions = [
    "What is HelpKart return policy?",
    "How long does refund take?",
    "Can I cancel after shipping?",
    "How can I contact support?"
]

for q in questions:
    print("\nQUESTION:", q)
    docs = retrieve_context(q, top_k=3)
    for i, doc in enumerate(docs, start=1):
        print(f"\nContext {i}:")
        print(doc["content"])
        print("Similarity:", doc["similarity"])