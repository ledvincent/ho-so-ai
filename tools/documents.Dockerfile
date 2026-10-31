FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends libreoffice-writer fonts-dejavu fonts-liberation && rm -rf /var/lib/apt/lists/*
ENTRYPOINT ["libreoffice", "-env:UserInstallation=file:///tmp/lo-profile", "--headless", "--convert-to", "pdf", "--outdir", "/out"]
