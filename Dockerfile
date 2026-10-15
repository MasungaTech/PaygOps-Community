FROM python:3.14.5-slim-bookworm

RUN apt-get -qq update && apt-get install -qq -y curl git postgresql-client

WORKDIR /
ENV PYTHONPATH /crm
ENV EDITION=oss
ENV ENABLE_ENTERPRISE_FEATURES=0

COPY requirements.txt /crm/
RUN pip install --upgrade pip
RUN pip install -r /crm/requirements.txt

COPY . /crm/

# Compile installed code (libraries)
RUN python -c "import compileall; compileall.compile_path(maxlevels=10, quiet=1)"
# Compile our code
RUN python -m compileall /crm/

RUN chmod +x /crm/entrypoint.sh

ENV HOME /
ARG curr_version=NA
ARG commit_sha=NA
ENV VERSION=oss-$curr_version
ENV COMMIT_SHA=$commit_sha

RUN mkdir /crm/template_cache
RUN ENV_VAR=TEST BUILD_MODE=1 python3 /crm/shared/build_helpers.py

ENTRYPOINT ["bash", "/crm/entrypoint.sh"]
