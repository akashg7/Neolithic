# Krishi-Mitr: run the integrated app (backend + frontend)

The app no longer runs on fixtures. Every screen calls FastAPI, which is backed by seeded Postgres: a year of real Agmarknet prices plus a demo story.

## 1. Backend

**One step (server or laptop with Docker):**

```bash
cp .env.example .env     # set JWT_SECRET, SARVAM_API_KEY, POSTGRES_PASSWORD, MINIO_ROOT_PASSWORD
./deploy/deploy.sh       # build + start everything, wait until healthy, smoke-test
```

- **What runs:** nginx on port 80 serves the web app at `/` and proxies `/api/v1` and `/docs` to the API.
- **First boot:** on an empty database, the API builds the schema and loads the demo seed automatically.
- **Data:** stored in the named volumes `pgdata`, `redisdata` and `miniodata`. It survives rebuilds and redeploys. Only `docker compose down -v` erases it.
- **Ports:** only nginx publishes one. Postgres, Redis and MinIO aren't reachable from outside.
- **Demo-morning reset:** `./deploy/deploy.sh --reseed`. This resets the demo story and moves prices forward to end yesterday.
- **CI:** pushing to `main` or `integrated` runs `.github/workflows/deploy.yml`, which runs the tests and then `deploy/deploy.sh` on EC2 over SSH.
  - Secrets: `EC2_HOST`, `EC2_USER`, `EC2_SSH_KEY`, and optionally `EC2_APP_DIR`.
  - The server keeps its own `.env`.
- **HTTPS:** put a load balancer or Cloudflare in front, or add a 443 block with certbot to `deploy/nginx.conf`. The phone's microphone only works on HTTPS or localhost.

**Without Docker:** you need Postgres 18 with PostGIS, and Redis.

```bash
python -m scripts.seed_demo
uvicorn app.main:app --port 8000
```

**Re-run the seed on demo morning.** Prices are shifted so that the newest one is *yesterday*. Re-seeding moves them forward again, and it also resets every lot, offer and deal to the demo story.

### What the seed contains

| | |
|---|---|
| Reference | 19 districts, 14 crops, 34 mandis. IDs match the app exactly (`cmd_onion`, `mkt_lasalgaon`, `dist_nashik`). |
| Prices | 34,045 daily rows of **real Agmarknet data** for those crops and mandis. Dates are shifted +N days so the newest row is yesterday. Every row is stored with source **`ARCHIVE`**, and the app labels it that way. |
| Demo farmer | **9822011111**, रामभाऊ पाटील, Niphad (Nashik). Has 4 lots, 2 open offers on the onion lot, 1 deal in transit and 1 settled deal. |
| Buyers | **9822022222** Mehta Onion Traders · **9822022223** Agro Fresh Exports |
| FPO admin | 9822033333 |

### Signing in

- **Demo button** on the landing page or the phone screen. This calls `POST /auth/demo-login` and needs `DEMO_MODE=true`.
- **Any phone + OTP `123456`.** This needs `DEV_FIXED_OTP=123456`. There is no SMS provider yet.
- Both are **disabled when `ENV=production`**.

## 2. Frontend (Krishi-Mitr)

```bash
cd Krishi-Mitr && npm ci
API_PROXY_TARGET=http://localhost:8000 npx webpack serve --port 8080   # web
```

- **Web:** the app calls same-origin `/api/v1`. The dev server proxies that to `API_PROXY_TARGET`, so no CORS setup is needed.
- **Vercel:** replace `REPLACE_WITH_API_HOST` in `vercel.json` with the EC2 HTTPS host.
- **Phone, development build:** run `adb reverse tcp:8000 tcp:8000`, which uses `config.ts` `DEV_TRANSPORT`.
- **Phone, release build:** set `PROD_HOST` in `src/config.ts`.
- **Offline fallback:** if the network fails on the day, set `USE_FIXTURES = true` in `src/config.ts` and rebuild. Every screen then renders from fixtures.

## 3. What is still not backed by the server

| Feature | Behaviour today |
|---|---|
| FPO pool split (S16) | Illustrative. There is no `GET /pools/{id}` yet. |
| Buyer↔farmer chat (Talks) | Illustrative. There is no messaging backend. |
| Cotton | No prices in the last 30 days of the data window, so Home/Market show it as "illustrative". |
| Sugarcane | Not in the Agmarknet export, so Home/Market show it as "illustrative". |
| Crop chips' prices on Home | Static labels. The selected crop's card, chart, forecast and advice are live. |
| SMS OTP | No provider. Use `DEV_FIXED_OTP` or the demo login. |

## 4. Smoke test

```bash
B=http://localhost:8000/api/v1
TOK=$(curl -s -XPOST $B/auth/demo-login -H 'content-type: application/json' -d '{"role":"FARMER"}' | jq -r .token)
curl -s "$B/market/overview?commodity_id=cmd_onion&market_id=mkt_lasalgaon" | jq '.latest, .verdict.action'
curl -s $B/lots -H "Authorization: Bearer $TOK" | jq 'length'
```
