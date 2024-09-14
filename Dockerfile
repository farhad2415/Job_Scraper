FROM python:3.10-slim
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install pip requirements
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8004

# Command to run the application
CMD ["gunicorn", "--access-logfile", "-", "--workers", "1", "--bind", "0.0.0.0:8004", "job_scraper.wsgi:application"]
