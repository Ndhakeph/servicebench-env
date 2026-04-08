FROM python:3.11-slim

WORKDIR /app

# Install only what we need - pure Python, no heavy deps
COPY server/requirements.txt /app/server/requirements.txt
RUN pip install --no-cache-dir -r server/requirements.txt

# Copy all environment code
COPY . /app/

# Set PYTHONPATH so imports resolve correctly
ENV PYTHONPATH="/app"

EXPOSE 7860

# Health check using stdlib (no curl/wget needed)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/health')" || exit 1

# Start uvicorn on port 7860 (HF Spaces requirement)
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]
