release: ./manage.py migrate
web: gunicorn --bind 0.0.0.0:$PORT dkc.wsgi
worker: REMAP_SIGTERM=SIGQUIT celery --app dkc.celery worker --loglevel INFO --without-heartbeat
