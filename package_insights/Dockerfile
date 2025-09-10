FROM python:3.12-slim

WORKDIR /app

# Copy the entire package structure
COPY package_insights/ ./package_insights/
COPY requirements.txt ./
COPY package_insights_launcher.py ./

RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["python", "/app/package_insights_launcher.py"]
