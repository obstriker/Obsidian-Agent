# Use a Python base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system packages if needed
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Copy your app files
COPY . /app

# Install Python dependencies (if requirements.txt exists)
# Otherwise, manually install known dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install your custom library from GitHub
RUN pip install git+https://github.com/obstriker/WhatsappWebPy.git

# Expose port if needed (e.g. Flask app)
EXPOSE 5000

RUN apt update && apt install -y git
RUN pip install --no-cache-dir -r requirements.txt

# Assuming the entry point is grocery_list/agent.py
CMD ["python", "src/wwbot.py"]