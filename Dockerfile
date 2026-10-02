FROM python:3.14-slim

WORKDIR /app

# D'abord les dépendances : cette étape est mise en cache si requirements.txt ne change pas
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Ensuite le code de l'application
COPY src ./src

EXPOSE 5000
CMD ["python", "-m", "src.app"]