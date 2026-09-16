# Use an official lightweight Python image.
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install build dependencies (if any) and pip.
RUN python -m pip install --upgrade pip

# Copy only requirement files first for caching.
COPY requirements.txt .

# Install runtime dependencies.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source code.
COPY . .

# Expose the FastAPI default port.
EXPOSE 8000

# Environment variables (can be overridden at runtime).
ENV PYTHONUNBUFFERED=1

# Command to run the FastAPI server.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
