# Dependency locks

`backend/pyproject.toml` is the only source of direct dependency declarations.
Core installs NumPy, Pydantic and NetworkX; `dev` adds offline test tools and
lightweight drivers; `runtime` adds Streamlit, Chroma and CPU model execution.
`dev.txt` supports Python 3.11–3.12. `runtime.txt` targets Linux x86_64/Python 3.11
and explicitly selects PyTorch CPU wheels. Chroma's PostHog version preserves its
three-argument telemetry API. No model weights are downloaded at install/build.

Regenerate with uv 0.13.0 from the repository root:

```powershell
uv pip compile backend/pyproject.toml --extra dev --python-version 3.11 --output-file requirements/dev.txt
uv pip compile backend/pyproject.toml --extra runtime --python-version 3.11 --python-platform x86_64-unknown-linux-gnu --extra-index-url https://download.pytorch.org/whl/cpu --index-strategy unsafe-best-match --emit-index-url --output-file requirements/runtime.txt
```

Review any version changes and rerun the offline suite and Docker build. Moving
these files does not authorize changing runtime versions or stored embeddings.
