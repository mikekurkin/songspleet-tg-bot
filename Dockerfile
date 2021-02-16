FROM python:3.8

ARG TG_SONGSPLEETBOT_KEY

RUN mkdir -p /usr/app
WORKDIR /usr/app

COPY Aptfile .
RUN apt-get update && apt-get install -y $(cat Aptfile)

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ . 

CMD [ "python", "bot.py" ]