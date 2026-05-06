FROM python:3.13.0-slim

WORKDIR /app

# Create non-root user
RUN useradd -m sandboxuser

# Install dependencies (system-wide or allowed ones)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Switch to non-root
USER sandboxuser

ENV PYTHONUNBUFFERED=1

# Default command (main.py will be mounted at runtime)
CMD ["python", "main.py"]