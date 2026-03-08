# HelpKart Low-Latency AI Support Agent with RAG

## Architecture Overview

The system is built as a low-latency customer support agent for a fictional e-commerce company, HelpKart. It combines a FastAPI backend, Supabase PostgreSQL, vector retrieval, OpenAI generation, and a WebSocket-based frontend chat interface.

### High-Level Flow
1. The user sends a message from the frontend chat UI.
2. The backend receives the message over a WebSocket connection.
3. The message is stored in the `conversations` table with a session id.
4. The backend embeds the user query and retrieves the most relevant knowledge base chunks from Supabase using vector similarity search.
5. The retrieved context plus recent conversation history are sent to the LLM.
6. The assistant response is streamed back to the frontend incrementally.
7. The final assistant response is stored in the `conversations` table.

## Low-Latency Design Decisions

The system is designed for responsiveness instead of batch-style request/response interaction.

- **WebSockets** are used to keep a persistent bi-directional connection open between client and server.
- **Streaming responses** improve perceived speed because the user sees the answer as it is being generated.
- **Top-k retrieval** limits context size and reduces prompt bloat.
- **Sliding conversation window** prevents latency from increasing as the chat gets longer.
- **Focused context injection** keeps the model grounded while minimizing unnecessary tokens.

## RAG Implementation Details

The knowledge base is stored in the `knowledge_base` table in Supabase.

- HelpKart policies are split into chunks
- each chunk is embedded using `text-embedding-3-small`
- embeddings are stored in the `embedding` vector column
- query embeddings are matched using the `match_documents` SQL function
- the top 3 most relevant chunks are injected into the prompt

This allows the assistant to answer based on retrieved knowledge instead of relying only on model memory.

## Context and State Management

Conversation state is stored in the `conversations` table using a shared `session_id`.

- all messages are persisted
- only the most recent 8 messages are included in the prompt
- older context remains in the database
- this supports conversational continuity while keeping prompts small

If retrieval returns weak or missing context, the assistant is instructed not to hallucinate and to admit when information is unavailable.


## Database Design
The system uses Supabase PostgreSQL with four core tables:

- `customers`: stores customer profile data
- `orders`: stores order details and order state, linked to `customers` through `customer_id`
- `conversations`: stores chat history using `session_id`, role, message, and timestamp
- `knowledge_base`: stores HelpKart policy chunks and their vector embeddings for retrieval

### Relationships and Constraints
- `orders.customer_id` is a foreign key referencing `customers.id`
- `customers.id`, `orders.id`, `conversations.id`, and `knowledge_base.id` are primary keys
- `customers.email` is unique
- `conversations.session_id` groups all turns belonging to one live support session

### Indexing and Low-Latency Read Design
To support low-latency reads:
- an index is created on `orders.customer_id` for fast customer-order lookup
- an index is created on `conversations.session_id` for fast session-history retrieval
- the `knowledge_base.embedding` column is used with vector similarity search through the `match_documents` SQL function
- only the top few relevant chunks are retrieved per turn, which reduces prompt size and lowers response latency

## RAG Design

The knowledge base is split into compact policy chunks and embedded using `text-embedding-3-small`.  
At query time, the user message is embedded and matched against stored vectors in Supabase using the `match_documents` function.

### Retrieval Strategy
- only the top 3 most relevant chunks are retrieved (`top_k = 3`)
- this keeps the prompt small and lowers latency
- retrieving only high-signal context reduces noise and improves answer quality

### Hallucination Reduction
The assistant is instructed to use retrieved context as the primary source of truth.  
If retrieval returns weak or no relevant context, the backend falls back to `"No relevant knowledge found"` so the model can avoid inventing unsupported policies or details.

## Low-Latency API and Streaming Design

The backend uses **WebSockets** instead of standard request/response HTTP because the assignment requires fast, continuous, bi-directional interaction. WebSockets allow the client and server to exchange messages over a single persistent connection, which reduces repeated connection overhead and supports live conversational behavior.

### Why WebSockets over SSE
- WebSockets support **bi-directional communication**
- the client can send rapid follow-up messages without reopening a new request
- the server can stream replies incrementally over the same connection
- this makes the conversation feel more like a live support call than isolated chat turns

### Dropped or Slow Connections
The WebSocket handler uses `WebSocketDisconnect` to detect client disconnects cleanly. If the browser closes or the network drops, the session ends gracefully and the backend does not crash.

### Backpressure / Slow Client Handling
The current implementation streams small response chunks incrementally. Because only a single user-facing response stream is sent at a time, backpressure is limited in this prototype. In a production version, outgoing chunk buffering, timeouts, and per-client queue limits would be added to handle slow consumers more robustly.


## Context and State Management

The system stores all chat turns in the `conversations` table using a shared `session_id`.  
At response time, the backend loads only the **most recent conversation window** instead of sending the entire chat history to the model.

### Sliding Context Window
- only the latest 8 messages are included in the prompt
- older messages remain stored in the database but are not always sent to the model
- this prevents latency and token usage from increasing linearly as the conversation grows

### Long Conversation Behavior
When a session becomes long, the backend keeps the conversation state in the database but only injects a recent rolling window into the model. This preserves short-term conversational continuity while keeping prompts small.

### Trade-off: Speed vs Context Completeness
Using a sliding window improves latency and reduces cost, but older context may not always be included in the model prompt. This is an intentional trade-off to maintain fast, real-time interactions.

## Performance and Latency Considerations

### Where latency exists
The main sources of latency in the system are:
- embedding generation for the user query
- vector retrieval from Supabase
- LLM response generation
- network transfer between frontend and backend

### How latency is reduced
- WebSockets are used to avoid repeated HTTP connection overhead
- only the top 3 relevant knowledge chunks are retrieved per turn
- only the latest 8 conversation messages are sent to the model
- retrieval happens before generation so the model receives focused, high-signal context instead of the full knowledge base
- FastAPI handles the WebSocket connection asynchronously, which keeps the interaction responsive

### Simple latency measurement
For evaluation, latency can be measured in two ways:
- **time to first token/chunk**: how quickly the assistant begins responding
- **time to full response**: how long the entire answer takes to complete

In testing, the streamed design improves perceived responsiveness because users begin seeing the answer before the full completion is generated.


## Sample Conversation Transcript

**User:** What is HelpKart return policy?  
**Assistant:** HelpKart allows customers to return products within 7 days of delivery.

**User:** And how long does the refund take?  
**Assistant:** Refunds are processed within 5 business days after a return is approved.

**User:** Can I cancel my order after shipping?  
**Assistant:** No. Once an order is shipped, it cannot be cancelled. However, you can still return the product within 7 days of delivery.

**User:** How can I contact support?  
**Assistant:** HelpKart customer support is available 24/7 through chat or email.