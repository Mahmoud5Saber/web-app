# Stage 1: Build dependencies
FROM python:3.9 AS builder

WORKDIR /app

# Copy only requirements first to leverage caching
COPY requirements.txt .

# Install dependencies in a virtual environment
RUN python -m venv /venv && /venv/bin/pip install --no-cache-dir -r requirements.txt

# Stage 2: Production Image
FROM python:3.9-slim

WORKDIR /app

# Create a non-root user for security
RUN groupadd -g 1000 appgroup && \
    useradd -m -g appgroup -u 1000 appuser

# Copy the pre-installed dependencies from the builder stage
COPY --from=builder /venv /venv

# Copy application files
COPY . .

# Set permissions for non-root user
RUN chown -R appuser:appgroup /app

# Use non-root user
USER appuser

# Expose Flask's default port
EXPOSE 5050

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_ENV=production
ENV PATH="/venv/bin:$PATH"

# Run the application
CMD ["python", "app.py"]
