FROM python:3.11-slim
WORKDIR /app
COPY src /app/src
COPY pyproject.toml /app/
RUN pip install --no-cache-dir .
ENV API_URL=http://192.168.50.4:8787/infer
ENV NOTES_DIR=/notes
VOLUME ["/notes"]
ENTRYPOINT ["obsidian-note-gen"]
