FROM jupyter/base-notebook:latest

USER root

RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$UBUNTU_CODENAME") stable" \
    | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y docker-ce-cli \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/jovyan/.jupyter/lab/user-settings/@jupyterlab/apputils-extension \
    && echo '{"theme": "JupyterLab Dark"}' \
    > /home/jovyan/.jupyter/lab/user-settings/@jupyterlab/apputils-extension/themes.jupyterlab-settings \
    && fix-permissions /home/jovyan

RUN curl -fsSL https://opencode.ai/install | bash

RUN pip install "marimo>=0.19.11" marimo-jupyter-extension

RUN groupadd -f docker && usermod -aG docker jovyan

USER jovyan
