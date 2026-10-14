# Environment templates

Choose the template for the execution environment:

| Execution | Copy from | Local destination |
| --- | --- | --- |
| Docker Compose / PostgreSQL | `config/docker.env.example` | `.env.docker` |
| Native Streamlit / SQLite | `config/local.env.example` | `.env` |

Real files are ignored, excluded from Docker context and kept local. Existing
credentials and Compose database passwords are preserved during consolidation.
Compose reads `.env.docker` explicitly; native entrypoints load `.env` before
creating `Settings`. Process environment and optional Streamlit secrets are mapped
once by the presentation bridge. The core never reads Streamlit secrets or dotenv.

Native setup also needs `data/` and an explicit Alembic upgrade before launching
`python -m streamlit run apps/streamlit_legacy/main.py`. Keep BGE-M3/1024D defaults
when opening existing vectors. Configure a working Ollama model or cloud provider
for chat/quiz; empty API key values are valid for Ollama usage.
