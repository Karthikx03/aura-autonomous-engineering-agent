FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
# BUG: service actually listens on 8080 and starts from server.py
EXPOSE 3000
CMD ["python", "main.py"]
