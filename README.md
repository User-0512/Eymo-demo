# Eymo Demo

An educational content platform with AI-powered moderation, personalized feed recommendations, and gamification.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Application                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │   Auth   │  │ Content  │  │   Feed   │  │   Moderation     │ │
│  │  Router  │  │  Router  │  │  Router  │  │    Router        │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───────┬──────────┘ │
│       │              │             │                │            │
│  ┌────▼──────────────▼─────────────▼────────────────▼──────────┐ │
│  │                    Service Layer                             │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐ │ │
│  │  │  Auth    │ │  Grok    │ │  Content │ │  Recommender   │ │ │
│  │  │  Utils   │ │  Service │ │   DB     │ │  (Embeddings,  │ │ │
│  │  │ (JWT)    │ │ (xAI)    │ │  Models  │ │  Ranking, etc.)│ │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                           │                                       │
│  ┌────────────────────────▼──────────────────────────────────────┐│
│  │                    PostgreSQL (pgvector)                      ││
│  │            users · content · user_interactions                ││
│  │            human_review_queue · embeddings (384d)             ││
│  └───────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

- **Python 3.11+**
- **Docker** (for PostgreSQL with pgvector)
- **Poetry** or **pip** for dependency management
- **xAI API key** (optional, for Grok-powered moderation)

## Setup

### 1. Clone and Install Dependencies

```bash
git clone <repo-url> eymo-demo
cd eymo-demo
pip install -r requirements.txt
```

### 2. Start PostgreSQL (with pgvector)

```bash
make db-up
# or: docker-compose up -d
```

This starts a PostgreSQL 16 container with the pgvector extension on port 5432.

### 3. Configure Environment

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and set:

| Variable        | Description                    | Required |
|-----------------|--------------------------------|----------|
| `DATABASE_URL`  | PostgreSQL connection string   | Yes      |
| `XAI_API_KEY`   | xAI API key for Grok           | No*      |
| `JWT_SECRET_KEY`| Secret for JWT tokens          | Yes      |

\* Without `XAI_API_KEY`, the moderation service falls back to `pending_review` status for all content.

### 4. Run Database Migrations

```bash
make migrate
# or: alembic upgrade head
```

### 5. Start the API Server

```bash
uvicorn services.api.app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.
Interactive docs at `http://localhost:8000/docs`.

## API Endpoints

### Authentication (`/auth`)
| Method | Path          | Description                      |
|--------|---------------|----------------------------------|
| POST   | `/register`   | Register a new user              |
| POST   | `/login`      | Login (returns JWT tokens)       |
| POST   | `/refresh`    | Refresh access token             |
| GET    | `/me`         | Get current user profile         |

### Content (`/content`)
| Method | Path              | Description                      |
|--------|-------------------|----------------------------------|
| POST   | `/`               | Create content (with moderation) |
| GET    | `/`               | List content (paginated/filtered)|
| GET    | `/{id}`           | Get single content               |
| PUT    | `/{id}`           | Update content (author only)     |
| DELETE | `/{id}`           | Delete content (author only)     |

### Feed (`/feed`)
| Method | Path                        | Description                      |
|--------|-----------------------------|----------------------------------|
| GET    | `/{user_id}`                | Generate personalized feed       |
| POST   | `/{user_id}/click/{content_id}` | Log a click/view interaction |

### Moderation (`/moderation`)
| Method | Path                | Description                      |
|--------|---------------------|----------------------------------|
| GET    | `/check`            | Health check                     |
| GET    | `/pending`          | List items pending human review  |
| POST   | `/review/{id}`      | Approve/reject a review item     |
| POST   | `/fact-check`       | Fact-check a piece of text       |

### Other
| Method | Path             | Description                      |
|--------|------------------|----------------------------------|
| GET    | `/progress`      | Progress router (placeholder)    |
| GET    | `/verification`  | Verification router (placeholder)|

## Running Tests

```bash
# Run all tests
make test
# or: python -m pytest

# Run with verbose output
python -m pytest -v

# Run specific test file
python -m pytest tests/test_auth.py -v

# Run e2e tests
python -m pytest tests/e2e/ -v
```

The test suite includes:
- **18 tests** across 4 test files
- **Unit tests**: auth, content CRUD
- **Integration tests**: moderation pipeline (policy rules + Grok API)
- **E2E tests**: recommender pipeline (embeddings, candidate generation, ranking)

## Project Structure

```
eymo-demo/
├── alembic/                  # Database migrations
│   └── versions/             # Migration scripts
├── apps/                     # Frontend applications
│   ├── mobile/               # Mobile app (placeholder)
│   └── web/                  # Web app (Next.js)
├── data/                     # Data & notebooks
│   └── notebooks/            # Jupyter notebooks for EDA/experiments
├── docs/                     # Documentation
│   ├── architecture/         # System design docs
│   ├── decisions/            # Architecture Decision Records (ADRs)
│   └── prodct/               # Product specs
├── infra/                    # Infrastructure
│   ├── ci-cd/                # GitHub Actions workflows
│   ├── k8s/                  # Kubernetes manifests
│   └── terraform/            # Terraform configs
├── scripts/                  # Utility scripts
│   ├── generate_synthetic_users.py
│   ├── seed_demo_content.py
│   └── smoke_test.py
├── services/                 # Backend services
│   ├── api/                  # FastAPI application
│   │   └── app/
│   │       ├── core/         # Config
│   │       ├── routers/      # API route handlers
│   │       └── schemas/      # Pydantic schemas
│   ├── auth_utils.py         # JWT & password utilities
│   ├── content_db.py         # Content DB models
│   ├── database.py           # SQLAlchemy engine & session
│   ├── gamification/         # Quiz, spaced repetition, streaks
│   ├── grok_service.py       # xAI Grok API client
│   ├── ingestion/            # Celery tasks, uploads, thumbnails
│   ├── moderation/           # AI moderation pipeline
│   │   ├── auto_classifier/  # Content classification (Grok)
│   │   ├── fact_check/       # Fact-checking service
│   │   ├── human_review_queue.py
│   │   └── policy_rules.py   # Heuristic pre-filter
│   ├── recommender/          # Recommendation engine
│   │   ├── features/         # Embedding generation
│   │   ├── models/           # Candidate generation & ranking
│   │   └── evaluation/       # Metrics (precision@k, recall@k)
│   └── user_db.py            # User DB model
├── tests/                    # Test suite
│   ├── e2e/                  # End-to-end tests
│   ├── conftest.py           # Shared pytest fixtures
│   ├── test_auth.py          # Auth unit tests
│   └── test_content.py       # Content CRUD tests
├── docker-compose.yml        # PostgreSQL + pgvector
├── Makefile                  # Task runner
└── requirements.txt          # Python dependencies
```

## Tech Stack

| Component      | Technology                             |
|----------------|----------------------------------------|
| **Backend**    | Python 3.11, FastAPI, SQLAlchemy 2.0   |
| **Database**   | PostgreSQL 16 + pgvector               |
| **AI**         | xAI Grok 4.5, sentence-transformers    |
| **Auth**       | JWT (python-jose), bcrypt (passlib)    |
| **Async**      | Celery + Redis (ingestion pipeline)    |
| **Migrations** | Alembic                                |
| **Testing**    | pytest, httpx TestClient               |
| **Infra**      | Docker, Kubernetes, Terraform          |
