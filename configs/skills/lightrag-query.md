---
name: lightrag-query
version: 1.0.0
description: Query LightRAG knowledge base for context-aware answers
category: memory
tier: C1-C5

triggers:
  - "what is"
  - "how does"
  - "explain"
  - "describe"
  - "tell me about"
  - "find information"
  - "search knowledge"
  - "context"

capabilities:
  - semantic_search
  - context_retrieval
  - answer_generation
  - debug_mode

usage:
  before_reasoning: |
    Before answering complex questions, query LightRAG for relevant context:
    1. Use lightrag_query_knowledge with the user's question
    2. Review retrieved chunks and scores
    3. Use the context to inform your answer
    4. Cite sources when possible

  context_expansion: |
    When you need more context on a topic:
    1. Query LightRAG with specific terms
    2. Use debug=true to see exact retrieved chunks
    3. Incorporate relevant context into your reasoning
    4. Note confidence scores from retrieval

  knowledge_writing: |
    When writing new knowledge to the system:
    1. Use lightrag_ingest_documents with structured content
    2. Include metadata: source, author, date, tags
    3. Verify ingestion succeeded (check chunksCreated > 0)

examples:
  - query: "How does the task routing system work?"
    topK: 5
    debug: false

  - query: "What are the completion gates for C4 tasks?"
    topK: 3
    debug: true

performance_tips:
  - Use specific queries for better retrieval accuracy
  - Enable debug mode to verify context relevance
  - Check stats() periodically to monitor index health
  - Rebuild index after bulk ingestion

integration:
  hermes: "long_term_memory layer"
  zera: "researcher mode context source"
  agent_os: "knowledge_retrieval middleware"
