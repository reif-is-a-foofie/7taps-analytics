# Use pre-built base image with all dependencies
# Base image is rebuilt only when requirements.txt changes
# This makes app-only changes deploy in ~30 seconds
ARG BASE_IMAGE=gcr.io/pol-a-477603/taps-analytics-ui-base:latest
FROM ${BASE_IMAGE}

# Set working directory (already set in base, but explicit is good)
WORKDIR /app

# Copy application code (only thing that changes frequently)
COPY app/ ./app/

# Note: .env is not copied - secrets come from GCP Secret Manager in production
# Note: Dependencies are already installed in base image

# Expose port (Cloud Run uses PORT env var, default to 8080)
EXPOSE 8080

# Health check for Cloud Run
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the application with optimized settings
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1"]
