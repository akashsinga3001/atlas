FROM python:3.11-slim

WORKDIR /app

ENV PYTHONPATH=/app

# Install System dependencies
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install Python dependencies
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose the port the app runs on
EXPOSE 8082

# Create a non-root user
RUN useradd -ms /bin/bash celeryuser
# Set permissions for /app
RUN chown -R celeryuser:celeryuser /app
# Switch to the new user
USER celeryuser