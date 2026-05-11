FROM jupyter/base-notebook:latest
USER root

# jupyterhub must match hub version for singleuser server binary
# marimo-jupyter-extension uses jupyter-server-proxy to embed marimo in JupyterLab
RUN pip install --no-cache-dir \
    "jupyterhub==5.*" \
    "marimo>=0.23.4" \
    marimo-jupyter-extension \
    jupyter-server-proxy

COPY jupyter_server_config.py /etc/jupyter/jupyter_server_config.py
RUN chmod 644 /etc/jupyter/jupyter_server_config.py

USER jovyan
