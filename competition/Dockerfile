FROM python:3.12-slim
WORKDIR /solution
COPY competition/requirements-runtime.txt /solution/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY solution.py /solution/solution.py
COPY backend/app/__init__.py /solution/backend/app/__init__.py
COPY backend/app/competition /solution/backend/app/competition
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "/solution/solution.py"]
CMD ["/task/task.md"]
