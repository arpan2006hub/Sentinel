# Sentinel frontend

A minimal investigator workspace for the Sentinel FastAPI backend. The UI only exposes actions and data backed by existing REST endpoints; it does not add mock dashboards, system settings, user profiles, or unsupported workflows.

## Requirements

- Node.js 20+
- Sentinel backend running at `http://localhost:8000`

## Setup

```powershell
cd frontend
if (!(Test-Path .env)) { Copy-Item .env.example .env }
npm install
npm run type-check
npm run lint
npm run build
npm run dev
```

Open `http://localhost:5173`.

Set `VITE_API_BASE_URL` in `.env` when the backend runs at a different address. The default is `http://localhost:8000/api`.

## Screens and API contracts

| UI | Backend endpoints |
|---|---|
| Case list and create | `GET /api/cases`, `POST /api/cases` |
| Case status | `PATCH /api/cases/{case_id}` |
| Case overview | `GET /api/cases/{case_id}/summary` |
| Analysis start and progress | `POST /api/analysis/start`, `GET /api/analysis/{run_id}` |
| Evidence list and source types | `GET /api/evidence?case_id=`, `GET /api/evidence/source-types` |
| Evidence upload | `POST /api/evidence` |
| Evidence integrity and custody | `GET /api/evidence/{id}/verify`, `GET /api/evidence/{id}/audit`, `GET /api/evidence/{id}/audit/verify` |
| Evidence download | `GET /api/evidence/{id}/file` |
| Timeline | `GET /api/timeline/{case_id}` |
| Anomaly list and details | `GET /api/anomalies/{case_id}`, `GET /api/anomalies/{case_id}/{anomaly_id}` |
| Evidence graph | `GET /api/graph/{case_id}?format=cytoscape` |
| Ranked entity leads | `GET /api/cases/{case_id}/suspects` |
| API health indicator | `GET /health` |

The interface uses locally copied shadcn/ui-style primitives built on Radix UI, Tailwind CSS, class-variance-authority and Lucide icons. No external UI CDN is used.

## Notes

- Analysis defaults to `include_video=false` because raw video inference can be CPU-intensive. It can be enabled explicitly on the case overview.
- Timeline date filters are sent as ISO 8601 `from` and `to` query parameters.
- Risk scores and entity rankings are displayed as investigative leads, not findings of wrongdoing.
- The backend currently has no authentication endpoints; this frontend therefore does not show a login page or fake user profile.
