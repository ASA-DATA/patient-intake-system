FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .

RUN python -m pip install --no-cache-dir pip==25.2 \
    && python -m pip install --no-cache-dir -r requirements.txt \
    && python -m pip check

COPY . .

EXPOSE 8000

CMD ["gunicorn" ,"-w" , "1","-k" , "uvicorn.workers.UvicornWorker","-b" , "0.0.0.0:8000","app.main:app"]
