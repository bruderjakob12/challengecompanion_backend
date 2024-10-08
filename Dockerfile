FROM tiangolo/uwsgi-nginx-flask:python3.11

COPY ./requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir --upgrade -r /app/requirements.txt

COPY ./app.py /app/main.py
COPY ./static /app/static
RUN mkdir templates
COPY ./templates /app/templates
COPY ./uwsgi.ini /app/uwsgi.ini
