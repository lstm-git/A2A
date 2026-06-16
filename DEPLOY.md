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

## Reverse proxy / hub

Exposed on the trackon site as `https://trackon.lstmed.ac.uk/A2A/`. The route
lives in the trackon repo (`Catering_orders/ontrack-nginx.conf`, the copy of the
live nginx config) and a card on `index.html` links to it. The app is prefix-aware
via `ProxyFix` + the `X-Forwarded-Prefix /A2A` header nginx sends.

Deploy steps on the VM:

```bash
# 1. A2A app (this repo) — picks up ProxyFix etc. No new deps (werkzeug ships
#    with Flask).
cd /opt/trackon/A2A && git pull
sudo systemctl restart a2a

# 2. trackon repo — picks up the nginx route + the hub card.
cd /opt/trackon && sudo git pull
#    Copy the updated config over the LIVE site file, then test + reload.
#    (Confirm the live filename first: ls /etc/nginx/sites-enabled/)
sudo cp /opt/trackon/Catering_orders/ontrack-nginx.conf /etc/nginx/sites-enabled/trackon
sudo nginx -t && sudo systemctl reload nginx
```

Then browse `https://trackon.lstmed.ac.uk/A2A/`.

## Notes
- `app.py` reads `HOST`/`PORT` from the environment (set in `a2a.service`);
  `.env` (the `ENTRA_*` secrets) is loaded by `load_dotenv()`.
- Logs: `journalctl -u a2a -f`.
