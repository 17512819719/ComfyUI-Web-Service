FROM python:3.10-slim

WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

COPY backend/app ./app
COPY backend/uploads ./uploads
COPY backend/outputs ./outputs
COPY backend/config.yaml ./

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]