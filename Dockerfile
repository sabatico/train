# Spell Quest — demo container. Serves the Flask app via gunicorn.
# The child's runtime data (data/students) is a mounted volume; word banks +
# audio + code are baked in. No secrets in the image (agent stays in canned-
# feedback mode unless DEEPSEEK_API_KEY + SPELLQUEST_AGENT_LIVE are passed at run).
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

# app code + baked content (word banks + dictation audio)
COPY app.py .
COPY engine ./engine
COPY agent ./agent
COPY templates ./templates
COPY static ./static
COPY data/word_bank ./data/word_bank

EXPOSE 8000
# 1 worker (the file store isn't multi-writer-safe) + threads for concurrent reads.
CMD ["gunicorn", "-w", "1", "--threads", "8", "-b", "0.0.0.0:8000", "--access-logfile", "-", "app:app"]
