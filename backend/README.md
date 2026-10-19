# TaskForge Backend Engine

FastAPI backend application and asynchronous background worker engine.

## Structure
- `app/api/v1/`: Versioned API route handlers.
- `app/core/`: Configuration via Pydantic Settings, structured JSON logging.
- `app/models/`: SQLAlchemy ORM models.
- `app/schemas/`: Pydantic request and response schemas.
- `app/services/`: Business logic and outbox dispatcher.
- `app/workers/`: Worker pool, process loop, and task registry.
- `app/queue/`: Supabase Queues (pgmq) and table queue adapters.
- `app/observability/`: Elasticsearch event publisher.
- `app/ai/`: CrewAI failure investigator.
- `tests/`: Pytest suite.

## Development
```bash
python -m uvicorn app.main:app --reload --port 8000
```
Run tests:
```bash
python -m pytest tests -v
```
