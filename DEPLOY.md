# A2A Deployment (OnTrack VM)

Runs as a standalone Flask app on `127.0.0.1:8091`, behind the existing reverse
proxy. Secrets live only in `/opt/trackon/A2A/.env` (never committed).

## First-time setup

```bash
# 1. Clone (own git repo, nested under /opt/trackon)
cd /opt/trackon
git clone https://github.com/lstm-git/A2A.git

# 2. Secrets — copy the three ENTRA_* values from ontrack-api
cd /opt/trackon/A2A
cp .env.example .env
grep ENTRA_ /opt/ontrack-api/.env   # paste these into .env, then set SECRET_KEY
nano .env

# 3. venv + dependencies
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

# 4. Permissions (app runs as www-data)
sudo chown -R www-data:www-data /opt/trackon/A2A
sudo chmod 600 .env

# 5. Install the service
sudo cp a2a.service /etc/systemd/system/a2a.service
sudo systemctl daemon-reload
sudo systemctl enable --now a2a
sudo systemctl status a2a
```

## Update / redeploy

```bash
cd /opt/trackon/A2A
git pull
./venv/bin/pip install -r requirements.txt   # only if requirements changed
sudo systemctl restart a2a
```

## Reverse proxy

Add a route that forwards to `http://127.0.0.1:8091`, matching how
`/opt/ontrack-api` (port 5000) is exposed on `:8090`.

## Notes
- `app.py` reads `HOST`/`PORT` from the environment (set in `a2a.service`);
  `.env` (the `ENTRA_*` secrets) is loaded by `load_dotenv()`.
- Logs: `journalctl -u a2a -f`.
