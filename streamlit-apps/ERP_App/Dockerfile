# Use official lightweight Python image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY app.py .
COPY game_engine.py .
COPY ui/ ./ui/

# Expose Streamlit port
EXPOSE 8080

# Command to run the application
# server.port 8080 is required for Cloud Run
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
