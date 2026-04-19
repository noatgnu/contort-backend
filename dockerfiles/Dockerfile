# docker build -f dockerfiles/Dockerfile-base -t noatgnu/contort-base:0.1.1 .
FROM noatgnu/contort-base:0.1.1

EXPOSE 8000
CMD ["gunicorn", "--workers=2", "contort.asgi:application", "--bind", "0.0.0.0:8000", "--log-level=debug","--timeout", "300", "-k", "uvicorn.workers.UvicornWorker"]