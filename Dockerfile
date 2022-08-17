FROM ubuntu:18.04
COPY . /imageV1/*
RUN pip install -r requirements.txt
RUN pip install -e git+https://github.com/twintproject/twint.git@origin/master#egg=twint
CMD python /blob/main/run.py