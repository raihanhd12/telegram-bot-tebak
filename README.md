# FastAPI Starter Template 🚀

A production-ready FastAPI starter template with best practices, clean architecture, Poetry for dependency management, and comprehensive tooling.

## ✨ Features

### Core Features

- **🚀 Modern FastAPI Setup**: FastAPI + uvicorn with async/await
- **📦 Poetry**: Modern Python dependency management and packaging
- **🗄️ Database Integration**: SQLAlchemy 2.x + Alembic migrations (PostgreSQL recommended)
- **🔐 Authentication Scaffolding**: JWT-ready structure with passlib + bcrypt
- **📚 API Documentation**: OpenAPI/Swagger available at `/docs`
- **🌐 CORS Support**: Configurable CORS middleware
- **⚙️ Environment Configuration**: `.env`-driven configuration with enhanced parsing
- **📝 Structured Logging**: Loguru integration for better logging

### Developer Experience

- **🧪 Testing**: pytest with async support and coverage
- **🎨 Code Formatting**: black + isort for consistent style
- **🔍 Linting**: ruff for fast Python linting
- **🔎 Type Checking**: mypy for static type analysis
- **🐳 Docker**: Multi-stage Docker build with Poetry
- **🔌 WebSocket Support**: Real-time communication with connection management
- **🏗️ Service Layer Architecture**: Clean separation (Controller → Service → Model)
- **⚠️ Error Handling**: Centralized exception handling with structured responses
- **✅ Request Validation**: Pydantic v2 models for request/response validation
- **📊 Database Migrations**: Alembic integration for schema management
- **💚 Health Checks**: Built-in monitoring endpoints

## 🏗️ Project Structure

```text
fastapi-starter/
├── main.py                 # Application entry point
├── pyproject.toml          # Poetry dependencies & tool config
├── alembic.ini             # Alembic configuration
├── Dockerfile              # Multi-stage Docker build
├── .env.example            # Environment template
├── .dockerignore           # Docker exclusions
├── src/
│   ├── app/
│   │   ├── controllers/    # HTTP controllers (API layer)
│   │   ├── models/         # SQLAlchemy models
│   │   ├── repositories/   # Database access layer
│   │   ├── schemas/        # Pydantic v2 schemas
│   │   ├── services/       # Business logic layer
│   │   └── middleware/     # FastAPI middleware
│   ├── config/
│   │   └── env.py          # Environment configuration
│   ├── database/
│   │   ├── session.py      # SQLAlchemy engine/SessionLocal/Base
│   │   ├── factories/      # Model registration for migrations
│   │   └── migrations/     # Alembic env + versions
│   ├── routes/             # API routers grouped by version
│   │   └── api/v1/         # API v1 routes
│   ├── scripts/            # Utility scripts
│   └── utils/              # Helper utilities
└── tests/                  # Test files
    ├── conftest.py         # pytest fixtures
    └── test_*.py           # Test modules
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+ (tested with 3.12)
- PostgreSQL for production (SQLite available for development)
- Docker (optional, for containerized deployment)

### Installation

1. **Clone the repository**

```bash
git clone <your-repo-url>
cd fastapi-starter
```

2. **Install Poetry** (if not already installed)

```bash
curl -sSL https://install.python-poetry.org | python3 -
# Or: pip install poetry
```

3. **Install dependencies**

```bash
poetry install
```

4. **Activate the virtual environment** (optional, Poetry creates one automatically)

```bash
poetry shell
```

5. **Configure environment variables**

```bash
cp .env.example .env
# Edit .env with your settings (DATABASE_URL, API_KEY, etc.)
```

6. **Run database migrations**

```bash
# Create a migration
poetry run alembic revision --autogenerate -m "Initial migration"

# Apply migrations
poetry run alembic upgrade head

# Or use the fresh migration script (development only)
poetry run python src/scripts/migrate_fresh.py
```

7. **Start the application**

```bash
# Development with auto-reload
poetry run uvicorn main:app --reload --host 127.0.0.1 --port 8000

# Or use the entrypoint script
poetry run python main.py
```

Visit `http://localhost:8000/docs` for the interactive API documentation.

## 🐳 Docker Usage

Build and run with Docker:

```bash
# Build the image
docker build -t fastapi-starter .

# Run the container
docker run -p 8000:8000 --env-file .env fastapi-starter
```

## Configuration

The application uses environment variables for configuration. Key variables in `.env`:

```env
# Environment
ENVIRONMENT=development

# API
API_HOST=127.0.0.1
API_PORT=8000

# Security
SECRET_KEY=change-this-in-production
API_KEY=your-api-key-here

# Database
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/fastapi_db

# Server
WORKERS=1
RELOAD=true
LOG_LEVEL=DEBUG
```

## 🛠️ Development

### Code Quality Tools

```bash
# Format code
poetry run black src/ tests/
poetry run isort src/ tests/

# Lint code
poetry run ruff check src/ tests/

# Type checking
poetry run mypy src/

# Run all quality checks
poetry run black src/ tests/ && poetry run isort src/ tests/ && poetry run ruff check src/ tests/
```

### Testing

```bash
# Run tests
poetry run pytest

# With coverage
poetry run pytest --cov=src --cov-report=html

# Run specific test file
poetry run pytest tests/test_main.py
```

### Database Migrations

```bash
# Create a new migration
poetry run alembic revision --autogenerate -m "Description"

# Apply migrations
poetry run alembic upgrade head

# Roll back one migration
poetry run alembic downgrade -1

# View migration history
poetry run alembic history
```

## 📚 API Usage Examples

### Health Check

```bash
curl http://localhost:8000/health
```

### Create a User

```bash
curl -X POST "http://localhost:8000/api/v1/users/" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "email": "john@example.com",
    "password": "secretpassword",
    "full_name": "John Doe"
  }'
```

### Get User

```bash
curl http://localhost:8000/api/v1/users/1
```

### WebSocket Testing

Visit `http://localhost:8000/test-websocket` for the interactive WebSocket test page.

## 🎯 Customization

1. **Add new models**: Create SQLAlchemy models in `src/app/models/`
2. **Add new APIs**: Create route files in `src/routes/api/v1/`
3. **Add business logic**: Implement services in `src/app/services/`
4. **Add validation**: Create Pydantic schemas in `src/app/schemas/`
5. **Add middleware**: Custom middleware goes in `src/app/middleware/`

## 📦 Production Considerations

- Change `SECRET_KEY` and `API_KEY` in production
- Use PostgreSQL instead of SQLite
- Set `ENVIRONMENT=production` in `.env`
- Configure `WORKERS` based on your server capacity
- Use a proper reverse proxy (nginx/caddy)
- Enable HTTPS/TLS
- Set up proper logging and monitoring
- Use `poetry install --only main` for production builds

## 📝 License

This project is licensed under the MIT License.

---

**Happy coding!** 🚀
