# --- Stage 1: Build & Dependency Resolution ---
FROM python:3.10-slim AS builder

WORKDIR /build

# Install build dependencies + libs required to compile ML packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libopenblas0 \
    libgomp1 \
    libgfortran5 \
    && rm -rf /var/lib/apt/lists/*

# Optimize pip layers
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# --- Stage 2: Production Runtime ---
FROM python:3.10-slim

# Install runtime system libraries required by TensorFlow, NumPy, XGBoost
RUN apt-get update && apt-get install -y --no-install-recommends \
    libopenblas0 \
    libgomp1 \
    libgfortran5 \
    && rm -rf /var/lib/apt/lists/*

# Security: Avoid running as root
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
	PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Copy only the necessary runtime files from builder
COPY --from=builder --chown=user /root/.local /home/user/.local
COPY --chown=user . .

# Environment optimizations
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=api/app.py
ENV PORT=7860

# Metadata
LABEL maintainer="SHPSv2 Lead Engineer" \
      version="2.0.2" \
      description="Structural Health Prediction System Dashboard"

EXPOSE 7860

# Start Flask with Gunicorn for production concurrency
# - timeout 300: allows model warm-up (4 XGB + LSTM) on cold start
# - workers 2: prevents loading models 4x in RAM
# - access-logfile -: routes request logs to stdout for podman logs
CMD ["gunicorn", "--timeout", "300", "--bind", "0.0.0.0:7860", "--workers", "2", "--threads", "2", "--access-logfile", "-", "api.app:app"]
