# Используем базовый образ debian
FROM python:3.12

ENV TZ=Europe/Moscow
RUN apt-get update && apt-get install -y nano htop vim default-libmysqlclient-dev build-essential python3-mysqldb redis-server
RUN apt-get install -y wireguard iproute2 openresolv


# Устанавливаем пакеты системы 
# RUN apt-get update && apt-get install -y \
#     python3.10 \
#     python3-pip \
#     && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app
# COPY wg0.conf /etc/wireguard/

# Копируем файлы 
#не правильная архитектура нужно для каждого сервиса свой проект poetry а не один на всех
COPY . /app
# COPY ../poetry.lock /app
# COPY pyproject1.toml /app/pyproject.toml
# COPY ../../pyproject.toml /app/pyproject.toml
# Копируем файл requirements.txt в директорию /app контейнера
# COPY requirements.txt .env /app/

# Устанавливаем зависимости из requirements.txt
RUN pip3 install poetry
RUN pip3 install --upgrade setuptools
RUN poetry install


# RUN pip3 install flask
# Открываем порт 5000 (или любой другой необходимый порт)
# EXPOSE 5001

# a


# Копируем файл .env внутрь контейнера
# COPY .env authorized_key.json /app/
# CMD ["python3", "workTelegram.py"]
CMD ["poetry", "run", "python3", "fastapiWork.py"]
# CMD ["gunicorn", "wsgi:app", "-c", "wsgi_config.py"]
# gunicorn wsgi:app -c wsgi_config.py
