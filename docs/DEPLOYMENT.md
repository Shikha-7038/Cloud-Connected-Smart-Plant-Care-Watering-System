# Cloud Deployment

## Option A — Student / free-tier (recommended for this project)

| Layer | Service | Why |
|---|---|---|
| Frontend | Vercel or Netlify (free tier) | Zero-config static hosting for the Vite build |
| Backend | Render.com or Railway.app (free/hobby tier) | Deploys a FastAPI app straight from GitHub |
| Database | Supabase (free Postgres) or Neon.tech | Managed Postgres, free tier, gives you the "cloud database" checkbox for real |
| Auth | Handled by the backend itself (JWT) — no extra service needed | Keeps the stack simple and free |

Steps:
1. Push this repo to GitHub (see `docs/GITHUB_STRATEGY.md`).
2. **Database:** create a free Supabase project → copy its `DATABASE_URL`
   (Settings → Database → Connection string, "URI" format).
3. **Backend (Render):** New → Web Service → connect the repo →
   Build command `pip install -r requirements.txt` → Start command
   `uvicorn backend.app:app --host 0.0.0.0 --port $PORT` → add environment
   variables from `.env.example` (`DATABASE_URL`, `JWT_SECRET`,
   `CORS_ORIGINS=https://<your-frontend-domain>`).
4. **Frontend (Vercel):** New Project → import the repo → root directory
   `frontend` → framework preset "Vite" → environment variable
   `VITE_API_URL=https://<your-render-backend-url>`.
5. Run `python scripts/seed_demo.py` once against the deployed
   `DATABASE_URL` (locally, with the env var pointed at the cloud DB) to
   create a demo user + devices, or register through the UI.
6. Point the sensor simulator's `API_URL` at the deployed backend and run it
   from your laptop — this is exactly how a real remote ESP32 would behave.

## Option B — Enterprise-style cloud architecture (conceptual)

```
ESP32 / Simulator
      │ HTTPS
      ▼
 API Gateway  (AWS API Gateway / Azure API Management / GCP API Gateway)
      │
      ▼
 Serverless Function  (AWS Lambda / Azure Functions / GCP Cloud Functions)
      │
      ▼
 Managed / Time-Series DB  (DynamoDB or Timestream / Cosmos DB / Firestore)
      │
      ▼
 Notification Service  (SNS / Event Grid / Pub-Sub)  ──► email/SMS/push
      │
      ▼
 Dashboard (S3 + CloudFront static hosting / Static Web Apps / Firebase Hosting)
```

Mapping table:

| Concept | AWS | Azure | GCP |
|---|---|---|---|
| Ingest API | API Gateway | API Management | API Gateway |
| Compute | Lambda | Functions | Cloud Functions |
| Database | DynamoDB / Timestream | Cosmos DB | Firestore / Bigtable |
| Alerts | SNS | Event Grid | Pub/Sub |
| Static hosting | S3 + CloudFront | Static Web Apps | Firebase Hosting |
| Monitoring | CloudWatch | Monitor | Cloud Monitoring |

This project's own backend already speaks plain REST, so migrating from
Option A to Option B later means swapping the ingestion endpoint for an API
Gateway + Lambda pair that call the same `process_reading()` function —
the automation/watering logic itself does not change.
