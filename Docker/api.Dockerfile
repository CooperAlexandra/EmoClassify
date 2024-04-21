FROM python:3.11.4

WORKDIR /emotionrecognition

COPY requirements.txt /emotionrecognition/
RUN pip install -r requirements.txt

RUN apt-get -y update && apt-get -y upgrade && apt-get install -y ffmpeg

ARG HOST_ADRESS
ARG BACKEND_PORT

ENV HOST_ADRESS $HOST_ADRESS
ENV BACKEND_PORT $BACKEND_PORT

RUN mkdir /emotionrecognition/backend 
RUN mkdir /emotionrecognition/callback

COPY backend/__init__.py /emotionrecognition/backend
COPY backend/system.py /emotionrecognition/backend
COPY backend/video.py /emotionrecognition/backend
COPY backend/audio.py /emotionrecognition/backend
COPY backend/report.py /emotionrecognition/backend

COPY callback/__init__.py /emotionrecognition/callback
COPY callback/api.py /emotionrecognition/callback

CMD ["python3", "./callback/api.py"]
