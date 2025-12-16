FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (including updated OpenSSL for R2 SSL)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    openssl \
    ca-certificates \
    curl \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set timezone
ENV TZ=Asia/Shanghai

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src

# Run the backend
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
