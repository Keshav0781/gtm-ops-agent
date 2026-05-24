# ============================================
# GTM Ops Agent - Dockerfile
# Multi-stage build — same approach as Siemens
# Stage 1: Builder — installs dependencies
# Stage 2: Production — lean, secure runtime
# ============================================

# Stage 1 — Builder
# Install all dependencies here
FROM python:3.13-slim AS builder

# Set working directory
WORKDIR /app

# Copy requirements first
# Docker caches this layer — if requirements don't change
# it skips reinstalling packages on next build
# This saves significant build time at Siemens
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ============================================
# Stage 2 — Production
# Lean, secure runtime image
# ============================================
FROM python:3.13-slim AS production

# Set working directory
WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Create non-root user
# At Siemens running as root is never allowed
# Security best practice — mandatory in enterprise
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy application code
COPY . .

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
# Docker checks this every 30 seconds
# Same concept as Railway/Azure health probes
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

# Start the server
# No --reload in production — only in development
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]