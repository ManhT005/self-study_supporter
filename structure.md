ai-study-agent/
├── .env                          # API Keys — KHÔNG commit
├── .env.example
├── README.md
├── requirements.txt
├── app.py                        # Entry point Streamlit
│
├── src/
│   ├── config.py
│   │
│   ├── rag/                      # Sprint 1
│   │   ├── pdf_parser.py         # PyMuPDF: PDF/DOCX → text + metadata
│   │   ├── chunker.py            # Semantic chunking
│   │   ├── embedder.py           # Gemini Embedding + bge-m3 local
│   │   ├── vector_store.py       # ChromaDB: 2 collections
│   │   ├── bm25_index.py
│   │   └── hybrid_retriever.py   # RRF fusion
│   │
│   ├── llm/                      # Sprint 2
│   │   ├── llm_adapter.py        # Interface: chat(), stream(), call_with_tools()
│   │   ├── gemini_client.py
│   │   └── ollama_client.py
│   │
│   ├── agent/                    # Sprint 3
│   │   ├── orchestrator.py       # ReAct loop
│   │   ├── state.py
│   │   ├── prompt_templates.py
│   │   └── tools/
│   │       ├── base.py
│   │       ├── search_docs.py
│   │       ├── generate_quiz.py
│   │       ├── save_note.py
│   │       └── get_progress.py
│   │
│   ├── graph/                    # Sprint 4
│   │   ├── graph_builder.py      # LLM extract → NetworkX DiGraph
│   │   ├── graph_algorithms.py   # Topo sort, cycle detection
│   │   └── schemas.py
│   │
│   ├── memory/                   # Sprint 4
│   │   ├── short_term.py
│   │   ├── long_term.py
│   │   └── progress_db.py
│   │
│   └── eval/                     # Sprint 5
│       ├── eval_runner.py        # RAG-only vs Agent+RAG
│       ├── llm_judge.py
│       └── metrics.py
│
├── ui/                            # Sprint 6
│   ├── dashboard.py
│   └── components/
│       ├── sidebar.py
│       ├── graph_viewer.py
│       └── quiz_arena.py
│
├── data/
│   ├── demo_docs/
│   ├── chroma_db/                 # gitignore
│   └── eval_dataset.json
│
└── tests/
    ├── test_agent.py
    ├── test_graph.py
    └── eval_rag.py