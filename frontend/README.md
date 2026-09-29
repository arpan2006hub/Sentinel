# Frontend — Sentinel

> **Status**: Foundation only. The investigator dashboard has not been built yet.

---

## Responsibility

The Sentinel frontend is the investigator-facing dashboard. It communicates exclusively with the FastAPI backend over REST/HTTP.

The frontend is responsible for:
- Displaying investigation cases
- Providing an interface for evidence upload and management
- Presenting the unified event timeline
- Rendering the evidence relationship graph
- Surfacing anomaly details and investigative leads
- Providing a readable investigation summary

**The frontend does not perform AI processing, database operations, or evidence storage. All such operations are handled by the backend.**

---

## Technology

- **React 18** — component framework
- **TypeScript** — type safety throughout
- **Vite** — development build tool (fast HMR)
- **Tailwind CSS** — utility-first CSS (to be configured)
- **React Query (@tanstack/react-query)** — server state management and API caching
- **React Router** — client-side routing
- **Axios** — HTTP client
- **React Flow** or **Cytoscape.js** — evidence graph visualisation (to be chosen at implementation)
- **Recharts** — timeline charts and data visualisation

---

## Planned Pages

| Page | Route | Description |
|---|---|---|
| **Case Dashboard** | `/` | Overview of all investigation cases |
| **Case Overview** | `/cases/:id` | Summary of a specific case: evidence count, anomaly count, key findings |
| **Evidence Explorer** | `/cases/:id/evidence` | Browse, upload, and inspect evidence for a case |
| **Timeline** | `/cases/:id/timeline` | Unified chronological event timeline (filterable by actor, source, time range) |
| **Evidence Graph** | `/cases/:id/graph` | Interactive entity/event relationship graph |
| **Anomaly Details** | `/cases/:id/anomalies/:anomalyId` | Individual anomaly drill-down with supporting/contradicting evidence |
| **Investigation View** | `/cases/:id/investigation` | Synthesised investigative leads for human review |

---

## Backend Communication

The frontend communicates with the backend via:

```
VITE_API_BASE_URL=http://localhost:8000
```

All API calls are made through an Axios client configured with the base URL from the environment variable.

Example API calls:

```
GET  /cases
POST /cases
GET  /cases/{id}
POST /evidence
GET  /timeline/{case_id}
GET  /graph/{case_id}
GET  /anomalies/{case_id}
```

See [`docs/architecture/api-contract.md`](../docs/architecture/api-contract.md) for the full API contract.

---

## Directory Structure

```
frontend/
├── src/
│   ├── components/     # Reusable UI components
│   ├── pages/          # Page-level components (one per route)
│   ├── layouts/        # Shared layout wrappers
│   ├── hooks/          # Custom React hooks (API hooks, etc.)
│   ├── services/       # Axios API client and service functions
│   ├── types/          # TypeScript type definitions
│   └── utils/          # Utility functions
│
├── public/             # Static assets
├── package.json
└── README.md           # This file
```

---

## Getting Started

> **Prerequisites**: Node.js 20+

```bash
# Install dependencies
cd frontend
npm install

# Start the Vite development server
npm run dev
```

The dev server will be available at `http://localhost:5173` by default.

```bash
# Type checking
npm run type-check

# Lint
npm run lint

# Production build
npm run build
```

---

## Design Principles

- **Evidence, not verdicts** — the UI presents evidence and signals; it does not tell the investigator who is guilty
- **Confidence indicators** — every anomaly and event should display its confidence score
- **Source transparency** — every presented fact should be linkable to its source evidence
- **Human-readable** — timelines and graphs should be digestible by a non-technical investigator
- **Local-first** — all data is fetched from the local backend; no external services are called from the frontend

---

*Frontend implementation begins in `src/`. Start with the Case Dashboard page and evidence upload flow.*
