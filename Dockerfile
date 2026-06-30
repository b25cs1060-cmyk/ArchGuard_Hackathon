
FROM python:3.9-slim


USER root 

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

# Expose a port
EXPOSE 8000
CMD ["python", "main.py"]