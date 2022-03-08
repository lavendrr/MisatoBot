
from python:3.9

WORKDIR /app

COPY requirements.txt .
COPY misatobot.py .
COPY run_in_docker.sh .

RUN pip install -r requirements.txt

CMD ["/bin/bash" , "/app/run_in_docker.sh"] 
