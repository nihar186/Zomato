# Use an official lightweight Python runtime as a parent image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Set the working directory in the container
WORKDIR /app

# Install system dependencies (if any needed for pandas/pyarrow)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first to leverage Docker layer caching
COPY requirements.txt /app/

# Install python packages
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ /app/src/

# Expose the application port
EXPOSE 8000

# Run uvicorn server on startup
CMD ["sh", "-c", "uvicorn src.api.app:app --host 0.0.0.0 --port $PORT"]
