# pyopera
A streamlit app to visualize opera visits

## Run with Docker (local build)

```bash
cp .env.example .env   # fill in your AWS credentials
docker compose up -d --build
# open http://localhost:8501
```

## Run from a prebuilt image (no repo clone needed)

A Docker image is built automatically by GitHub Actions and published to
[GitHub Container Registry](https://github.com/papalotis/pyopera/pkgs/container/pyopera)
on every push to `main`.

On ZimaOS (or any Docker host), you only need the compose file — no clone:

```bash
# 1. Grab the compose file
curl -O https://raw.githubusercontent.com/papalotis/pyopera/main/docker-compose.ghcr.yml

# 2. Create .env with your AWS credentials
cp .env.example .env

# 3. Pull and run
docker compose -f docker-compose.ghcr.yml up -d
```

The image is public, so no login is required to pull it.

## Configuration

The app reads AWS credentials (for DynamoDB) from either environment variables
(`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`) or a Streamlit
`secrets.toml`. Both are gitignored and never committed.