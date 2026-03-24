FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY requirements-crewai.txt .
RUN pip install --no-cache-dir -r requirements-crewai.txt
RUN pip install --no-cache-dir \
    fastapi==0.115.0 \
    starlette==0.38.6 \
    uvicorn[standard]==0.42.0 \
    httpx==0.28.1 \
    pydantic==2.11.10 \
    pydantic-settings==2.10.1 \
    python-dotenv==1.2.2

COPY app ./app
COPY tests ./tests

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
