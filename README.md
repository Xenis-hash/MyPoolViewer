# MyPoolViewer

**Pool Configuration Platform** — automated equipment sizing, annotated blueprints, 3D visualisation, and PDF report generation for residential swimming pools.

## Overview

MyPoolViewer is a full-stack web application for pool construction specialists and their clients. Given pool dimensions, type, filtration system, liner, and fittings, it automatically selects and sizes all hydraulic equipment from the Fluidra 2025 commercial catalog, generates an annotated SVG blueprint and a programmatic 3D isometric view, and produces a downloadable 6-page PDF report.

## Features

- **6-step configuration wizard** — dimensions, pool type, filtration, liner (35 products), fittings, results
- **Live SVG canvas** — scales dynamically to pool aspect ratio as you type
- **Equipment calculator** — rule-based sizing against a 575-row Fluidra catalog CSV (EN 16713 standards)
- **Annotated blueprint** — top-down SVG with component positions, engine room, flow lines, dimension annotations
- **Isometric 3D view** — programmatic PIL rendering of pool body + engine room with component callouts
- **6-page PDF report** — dark blueprint theme, embedded blueprint PNG, 3D view, equipment schedule, full BOM
- **35 real liner products** — CGT Alkor and Renolit Alkorplan catalog swatches extracted via PIL

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | HTML5 / CSS3 / Vanilla JS (single-file SPA) |
| Backend | Python 3.12 / Flask 3 |
| Calculation | `calculator.py` — rule-based equipment selection |
| Blueprint | `blueprint.py` — programmatic SVG + cairosvg |
| 3D View | `iso3d.py` — PIL isometric projection |
| PDF Report | `report.py` — ReportLab 4 |
| Database | `master_pool_components.csv` — 575 rows, 23 columns |

## Project Structure

```
MyPoolViewer/
├── engine/
│   ├── static/
│   │   └── index.html          # Complete single-file frontend
│   ├── calculator.py           # Equipment sizing engine (45KB)
│   ├── blueprint.py            # SVG blueprint renderer (41KB)
│   ├── report.py               # PDF report generator
│   ├── iso3d.py                # Isometric 3D visualiser
│   ├── server.py               # Flask API server
│   └── master_pool_components.csv  # Fluidra equipment database
├── requirements.txt
└── README.md
```

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the server
cd engine
python server.py

# 3. Open in browser
# http://localhost:5000
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Serve the frontend |
| POST | `/api/calculate` | Calculate equipment + BOM from pool config |
| POST | `/api/report` | Generate and download PDF report |
| GET | `/api/options` | Database stats |

## Dataset

- **Primary:** Fluidra 2025 Commercial Catalog (7-part PDF, 700+ pages) — parsed into `master_pool_components.csv`
- **Liners:** CGT Alkor 2024 + Renolit Alkorplan 2024 catalogs — 35 products, swatch images extracted via PIL
- **Fittings:** Product photographs extracted from catalog pages, background-removed with PIL flood-fill

## Author

Andreas N. Xeni · U244N0653 · xenis.a@live.unic.ac.cy
