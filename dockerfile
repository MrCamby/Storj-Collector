FROM python
WORKDIR /app

RUN pip install datetime requests paramiko scp
CMD python -u collector.py