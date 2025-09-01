FROM python:3.10

WORKDIR /code

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /code/
RUN pip install -r requirements.txt

COPY . /code/

EXPOSE 8000
