# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Korean chatbot API system built on Google Cloud Discovery Engine, serving as a backend service for "처음소프트" company. The system provides intelligent question-answering using Discovery Engine's Answer API and Search API.

**Key Architecture**:
- **Backend**: FastAPI application (Python 3.11+) with modular structure
- **Search Engine**: Google Cloud Discovery Engine for document search and answer generation
- **Frontend**: Static HTML/CSS/JS files served separately via Firebase Hosting
- **Deployment**: Google Cloud Run for backend, Firebase Hosting for frontend

## Core Development Commands

### Automated Setup (Recommended for New Projects)
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your PROJECT_ID (minimum required)
# Then run automated setup
python setup.py

# This will automatically create:
# - Required GCP APIs activation
# - Discovery Engine datastore and engine
# - Cloud Storage bucket with CORS
# - Service account with proper permissions
# - Firebase setup (optional)
```

### Manual Development Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn main:app --reload --port 8000

# Set required environment variables (if not using automated setup)
export PROJECT_ID="your-gcp-project-id"
export DISCOVERY_LOCATION="global"
export DISCOVERY_COLLECTION="default_collection"
export DISCOVERY_ENGINE_ID="your-discovery-engine-id"
export DISCOVERY_SERVING_CONFIG="default_config"
```

### Testing
```bash
# Test health endpoints
curl http://localhost:8000/api/health
curl http://localhost:8000/api/health/detailed

# Test main API
curl -X POST http://localhost:8000/api/generate \
  -F "userPrompt=테스트 질문" \
  -F "conversationHistory=[]"
```

### Deployment
```bash
# Build and deploy to Cloud Run
gcloud builds submit --tag "gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
gcloud run deploy discovery-chatbot \
  --image="gcr.io/${PROJECT_ID}/${SERVICE_NAME}" \
  --platform=managed \
  --region="${DISCOVERY_LOCATION}" \
  --allow-unauthenticated \
  --set-env-vars="PROJECT_ID=${PROJECT_ID},..."

# Deploy frontend to Firebase
firebase deploy --only hosting
```

## Architecture Structure

### Modular Backend Design
The codebase follows a clean modular architecture:

- **`main.py`**: FastAPI application entry point with CORS, routing, and background authentication
- **`modules/config.py`**: Centralized environment variable management and Google Cloud resource path generation
- **`modules/auth.py`**: Google Cloud authentication handling (service accounts, default credentials, storage client)
- **`modules/routers/`**: FastAPI route handlers
  - `api.py`: Main API endpoints (`/api/generate`, `/api/health`, GCS proxy)
  - `discovery_only_api.py`: Discovery Engine-specific test endpoints
- **`modules/services/`**: Business logic layer
  - `discovery_engine_api.py`: Discovery Engine API client with session management and caching

### Discovery Engine Integration
The system uses a two-step approach:
1. **Search API**: Retrieves relevant documents from the datastore
2. **Answer API**: Generates contextual answers with citations and related questions

Key features:
- Session management for query continuity
- Authentication header caching (5-minute TTL)
- Fallback to search results when Answer API fails
- Korean language optimization (`languageCode: "ko"`)

### Frontend Separation
- Static files in `public/` directory
- Conditional serving: local development serves static files, Cloud Run deployment API-only
- Firebase Hosting handles frontend with API proxy to Cloud Run backend

## Authentication Requirements

The system requires Google Cloud service account credentials with:
- `roles/discoveryengine.editor` - Discovery Engine access
- `roles/storage.objectViewer` - Cloud Storage access

Authentication methods (in priority order):
1. Secret Manager JSON (Cloud Run production)
2. Local service account key file (`keys/cheom-kdb-test1-faf5cf87a1fd.json`)
3. Default Cloud Run service account

## API Endpoints

### Main Endpoints
- `POST /api/generate` - Main chatbot endpoint accepting form data (`userPrompt`, `conversationHistory`)
- `GET /api/health` - Basic health check
- `GET /api/health/detailed` - Health check with authentication status
- `POST /api/discovery-answer` - Direct Discovery Engine Answer API test

### Response Format
```json
{
  "answer": "Generated answer text",
  "citations": [...],
  "search_results": [...],
  "related_questions": [...],
  "updatedHistory": [...],
  "metadata": {
    "engine_type": "discovery_engine_main",
    "query_id": "...",
    "session_id": "..."
  }
}
```

## Configuration Management

Environment variables are managed through `modules/config.py` with validation and path generation:
- Discovery Engine settings (project, location, engine ID, serving config)
- Authentication paths and service account configuration
- System prompt loading from `prompt/prompt.txt`
- Dynamic API endpoint URL generation

## Error Handling

The system implements comprehensive error handling:
- Authentication failures → 503 Service Unavailable
- Discovery Engine errors → Graceful fallback to search results
- Background authentication initialization prevents blocking startup
- Structured logging with Korean language support

## Development Notes

- **Korean Language Focus**: All user-facing text and logging in Korean
- **Modular Design**: Each module has single responsibility (auth, config, services, routing)
- **Background Processing**: Authentication initialization runs in background thread
- **Session Management**: HTTP session reuse and connection pooling for Discovery Engine API
- **Caching Strategy**: Authentication headers cached for 5 minutes to reduce latency