FROM python:3.10.2

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --quiet -r requirements.txt

COPY . .

CMD bash -c "python manage.py makemigrations && python manage.py migrate && python manage.py runserver 0.0.0.0:8000"
