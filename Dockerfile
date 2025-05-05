FROM python:3.9-slim

# Install Chrome and dependencies for Selenium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    xvfb \
    libxi6 \
    libgconf-2-4 \
    default-jdk \
    chromium \
    chromium-driver

# Set display port to avoid crash
ENV DISPLAY=:99

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variable for Chrome
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Set port
ENV PORT 8080

# Run the application
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app