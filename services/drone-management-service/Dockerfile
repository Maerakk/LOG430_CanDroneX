FROM python:3.12-slim
WORKDIR /srv
COPY services/drone-management-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY common/candronex_common ./candronex_common
COPY services/drone-management-service/drone_management ./drone_management
COPY services/drone-management-service/openapi.yaml .
EXPOSE 8000
USER nobody
CMD gunicorn --bind 0.0.0.0:8000 --worker-class gthread --workers ${WEB_WORKERS:-2} --threads ${WEB_THREADS:-16} "drone_management.main:create_app()"
