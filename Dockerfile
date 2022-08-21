# Set base image (host OS)
FROM python:3.8

# By default, listen on port 5000
EXPOSE 5000/tcp

# Set the working directory in the container
WORKDIR /News

# Copy the dependencies file to the working directory
COPY requirements.txt config.py app.db app.py .
COPY Newsapp Newsapp
COPY Newsapp/static/js/jquery.js Newsapp/static/js

# Install any dependencies
RUN python -m pip install --upgrade pip
RUN apt install git
RUN pip install -e git+https://github.com/twintproject/twint.git@origin/master#egg=twint
RUN pip install -r requirements.txt

# Specify the command to run on container start
CMD [ "python", "app.py" ]
