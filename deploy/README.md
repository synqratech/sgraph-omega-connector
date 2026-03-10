# Deploy assets

- `compose/docker-compose.local.yml`: full local loop (connector + omega + sgraph + reverse proxy).
- `proxy/`: TLS-terminated reverse proxy simulation for local integration.
- `omega/`: omega runtime image with preinstalled API dependencies (avoids reinstall at each restart).
- Local compose uses bind mounts to upstream repositories via env vars:
  - `OMEGA_REPO_PATH` (default `../../../omega-repo`)
  - `SGRAPH_REPO_PATH` (default `../../../sgraph-repo`)
  Set them in `env/.env.local.example` to match your local clone paths.
- Connector calls Omega through proxy (`https://reverse-proxy:8088/omega`) in local loop.
- `reverse-proxy` mounts `proxy/nginx.conf` as a bind-volume, so nginx body-limit changes apply after container recreate (`make proxy-recreate`) without image rebuild.
- `omega-api` runs with configurable worker count (`OMEGA_UVICORN_WORKERS`) and bounded BLAS threads (`OMEGA_OMP_NUM_THREADS`, `OMEGA_OPENBLAS_NUM_THREADS`) for single-host stability.
