# ANTI-PATTERN 1: Using the 'latest' tag. 
# This breaks reproducibility and can inject breaking changes unpredictably.
FROM python:latest

# ANTI-PATTERN 2: Running as the default 'root' user.
# If the container is compromised, the attacker has root access.
WORKDIR /app

# ANTI-PATTERN 3: Copying absolutely everything (including local .env files if not ignored properly).
COPY . .

# ANTI-PATTERN 4: Hardcoding sensitive environment variables in the Dockerfile.
ENV DATABASE_URL="postgres://admin:supersecretpassword123@db.production.internal:5432/main"

RUN pip install requests flask

EXPOSE 8000

# ANTI-PATTERN 5: Running a production application using the dev server instead of gunicorn/uvicorn.
CMD ["python", "test.py"]