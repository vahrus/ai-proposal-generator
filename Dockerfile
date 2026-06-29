FROM python:3.11-slim

WORKDIR /app

# Зависимости устанавливаем отдельным слоем — кэшируются при неизменном requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Папка для экспортируемых файлов
RUN mkdir -p outputs

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "app:app"]
