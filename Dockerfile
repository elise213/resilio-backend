# Use an official Python runtime as a parent image
FROM python:3.10-slim-buster

# Set the working directory in the container to /app
WORKDIR /app

# Add the current directory contents into the container at /app
ADD . /app

# Install any needed packages specified in requirements.txt
# RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --use-feature=fast-deps -r requirements.txt


# Make port 3000 available to the world outside this container
EXPOSE 3000

# Run gunicorn when the container launches
# CMD gunicorn wsgi --bind 0.0.0.0:3000 --chdir ./
CMD gunicorn --worker-class gevent wsgi --bind 0.0.0.0:3000 --chdir ./