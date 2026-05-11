# Runs inside each user's JupyterLab container.
# JupyterHub injects JUPYTERHUB_SERVICE_PREFIX / base_url automatically.
c.ServerApp.ip = "0.0.0.0"

# marimo-jupyter-extension (jupyter-server-proxy) config
c.MarimoProxyConfig.no_sandbox = True
c.MarimoProxyConfig.marimo_path = "/opt/conda/bin/marimo"
c.MarimoProxyConfig.host = "127.0.0.1"   # override ::1 IPv6 detection
c.MarimoProxyConfig.timeout = 120
c.MarimoProxyConfig.skip_update_check = True
