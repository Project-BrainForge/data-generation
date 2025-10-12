# Use a base Python image
FROM python:3.8-slim

# Set working directory
WORKDIR /app

# Install dependencies for octave and necessary build tools
RUN apt-get update && apt-get install -y \
    octave \
    liboctave-dev \
    build-essential \
    && apt-get clean

# Install the 'control' package first, as 'signal' depends on it
RUN octave --eval "pkg install -forge control"

# Now install the 'signal' package
RUN octave --eval "pkg install -forge signal"

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install -r requirements.txt

# Copy the rest of the application code
COPY . /app

#create source directory
RUN mkdir -p /app/source

# Run Octave to load the signal package
RUN octave --eval "pkg load signal"

# Run the Python script
CMD ["python", "forward/pipeline_orchestrator.py", "--start_region", "0", "--end_region", "2"]
