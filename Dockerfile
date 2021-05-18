FROM python:slim-buster

RUN pip install \
    requests m3u8 bs4 pycryptodome lxml

WORKDIR /work