# Use the official Playwright image which includes Python and browsers
# This is much safer than trying to install dependencies manually on slim
FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy

WORKDIR /app

# Copy requirements first to cache dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose port for Streamlit (Cloud Run uses 8080 by default)
EXPOSE 8080

# Environment variables
ENV PORT=8080
ENV HEADLESS=true
# Install tzdata and configure timezone
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y tzdata && \
    ln -fs /usr/share/zoneinfo/Asia/Taipei /etc/localtime && \
    echo "Asia/Taipei" > /etc/timezone && \
    dpkg-reconfigure -f noninteractive tzdata && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

ENV USE_FIRESTORE=true
ENV TZ=Asia/Taipei

# Run Streamlit
CMD streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
