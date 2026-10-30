FROM python:3.12-slim
WORKDIR /srv
COPY services/service-ordering-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY common/candronex_common ./candronex_common
COPY services/service-ordering-service/service_ordering ./service_ordering
COPY services/service-ordering-service/openapi.yaml .
EXPOSE 8000
USER nobody
CMD gunicorn --bind 0.0.0.0:8000 --worker-class gthread --workers ${WEB_WORKERS:-2} --threads ${WEB_THREADS:-16} "service_ordering.main:create_app()"
