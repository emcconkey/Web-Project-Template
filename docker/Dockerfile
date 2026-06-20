FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p logs

EXPOSE 5000

# gunicorn serves the app factory's module-level `app` (app.py: app = create_app()).
# The full template runs `flask db upgrade &&` first; this sample has no database
# or migrations, so it's omitted.
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:5000 --workers 4 \
     --access-logfile logs/access.log --error-logfile logs/error.log app:app"]
