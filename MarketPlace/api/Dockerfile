#download the python image
FROM python:3.7.7

#set a directory for the app
WORKDIR /app

COPY requirements.txt requirements.txt

#install dependencies
RUN pip install -r requirements.txt

COPY . /app

#create database
RUN ls
RUN chmod +x entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]



