FROM docker.io/python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy requirements.txt and install dependencies
COPY requirements.txt .

RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    libssl-dev \
    libavdevice-dev \
    libavfilter-dev \
    libavformat-dev \
    libavcodec-dev \
    libavutil-dev \
    libswscale-dev \
    libswresample-dev \
 && pip install --upgrade pip \
 && pip install --retries=10 -r requirements.txt \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy the rest of the application code
COPY . .

# Expose the application port
EXPOSE 8000

# Run the main application
CMD ["python3", "main.py"]
