FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt
RUN apt-get update && apt-get install -y iptables
COPY iptables-setup.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/iptables-setup.sh


COPY main.py .

CMD ["python3", "main.py"]
