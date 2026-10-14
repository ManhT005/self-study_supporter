FROM python:3.11-slim-bookworm AS legacy
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/home/study \
    HF_HOME=/home/study/.cache/huggingface \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
WORKDIR /app
RUN apt-get update \
    && apt-get install --no-install-recommends -y libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY requirements/runtime.txt ./requirements/runtime.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements/runtime.txt
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin study \
    && mkdir -p /app/data /home/study/.cache/huggingface \
    && chown -R study:study /app/data /home/study
COPY --chown=study:study . .
RUN python -m pip install --no-deps ./backend
USER study
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=5)"]
CMD ["python", "-m", "streamlit", "run", "apps/streamlit_legacy/main.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]

# Additive API target. The final default stage still runs the legacy app.
FROM legacy AS api
USER root
RUN python -m pip install -r requirements/api.txt
USER study
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=5 CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=4)"]
CMD ["python", "-m", "uvicorn", "apps.api.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-proxy-headers"]

FROM legacy AS streamlit
