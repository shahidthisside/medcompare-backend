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
    && rm -rf /var/lib/apt/lists/*

# Install ChromeDriver for Chromium 136.0.7103.59
RUN wget -q -O /tmp/chromedriver.zip "https://storage.googleapis.com/chrome-for-testing-public/136.0.7103.59/linux64/chromedriver-linux64.zip" || { echo "Failed to download ChromeDriver"; exit 1; } && \
    unzip /tmp/chromedriver.zip -d /tmp && \
    mv /tmp/chromedriver-linux64/chromedriver /usr/bin/chromedriver && \
    chmod +x /usr/bin/chromedriver && \
    rm -rf /tmp/chromedriver.zip /tmp/chromedriver-linux64

# Set display port to avoid crash
ENV DISPLAY=:99

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables for Chrome
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Set port
ENV PORT=8080

# Run the application (JSON format for CMD)
CMD ["gunicorn", "--bind", ":8080", "--workers", "1", "--threads", "8", "--timeout", "0", "app:app"]