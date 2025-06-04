# Use Java 17 as base
FROM openjdk:17-slim

RUN apt-get update && \
    apt-get install -y curl python3 python3-venv python3-pip && \
    ln -s /usr/bin/python3 /usr/bin/python

WORKDIR /app
COPY clean_job.py /app
COPY requirements.txt /app

RUN pip3 install -r requirements.txt 

RUN curl -O https://downloads.apache.org/spark/spark-3.5.6/spark-3.5.6-bin-hadoop3.tgz && \
    tar -xvzf spark-3.5.6-bin-hadoop3.tgz -C /opt && \
    mv /opt/spark-3.5.6-bin-hadoop3 /opt/spark && \
    rm spark-3.5.6-bin-hadoop3.tgz

ENV SPARK_HOME=/opt/spark
ENV PATH="${SPARK_HOME}/bin:$PATH"

ENTRYPOINT ["python", "/app/clean_job.py"]

CMD []