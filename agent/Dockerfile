# The deployment agent (agent/README.md). Built from the repository root:
#   docker build -f agent/Dockerfile .
FROM python:3.13-alpine

# The Docker CLI and Compose: the agent drives the host's Docker through its socket.
RUN apk add --no-cache docker-cli docker-cli-compose

ARG AGENT_VERSION=dev
ENV AGENT_VERSION=${AGENT_VERSION} PYTHONUNBUFFERED=1

WORKDIR /agent
COPY agent/urban_agent ./urban_agent

ENTRYPOINT ["python", "-m", "urban_agent"]
