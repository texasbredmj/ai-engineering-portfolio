FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm
# Yarn is not used by this environment. Remove its stale optional apt source before
# the Docker feature runs apt-get; Debian signature verification remains enabled.
RUN rm -f /etc/apt/sources.list.d/yarn.list /etc/apt/sources.list.d/yarn.sources
