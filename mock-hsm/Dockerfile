FROM python:3.11-slim
WORKDIR /app
RUN pip install flask
COPY main.py /app/main.py
EXPOSE 9000
CMD ["python","/app/main.py"]
