# Neurobotika Phase 1 — Data Download
# Slim CPU image: aws cli + git-annex for fetching the source MRI datasets.
#
# Build:
#   docker build -f docker/download.Dockerfile -t neurobotika-download .
#
# Run locally:
#   docker run --rm -e AWS_REGION=eu-central-1 neurobotika-download \
#     bash /app/01/run_downloads.sh --dataset mgh --subject sub-EXC004 \
#     --s3-dest s3://neurobotika-data/raw/mgh_100um

FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        git-annex \
        unzip \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
        awscli \
        boto3 \
        nibabel \
        numpy \
        click

COPY pipeline/01_data_acquisition/ /app/01/

RUN chmod +x /app/01/*.sh

WORKDIR /app

CMD ["bash", "/app/01/run_downloads.sh", "--help"]
