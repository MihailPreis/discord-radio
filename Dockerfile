FROM python:3.8-slim

WORKDIR /app
VOLUME /app/data

COPY DiscordRadio.py .
COPY requirements.txt .

RUN set -x \
    && apt-get update \
    && apt-get upgrade \
    && apt-get install -y --no-install-recommends ffmpeg

RUN pip install -r requirements.txt

CMD [ "python", "./DiscordRadio.py" ]
