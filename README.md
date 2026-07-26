# Exan — AI Exam Scanner & Grader

An AI-powered application that scans exam documents, extracts their structure, and automatically grades student responses. Supports both cloud AI providers and fully offline local inference.

## How It Works

1. **Upload Empty Exam** — Upload a blank exam (PDF or image). The AI identifies all questions, their types, and point values.
2. **Upload Answer Key** — Upload the same exam filled in with correct answers.
3. **Grade Student Exams** — Upload one or more completed student exams. Each is graded automatically against the answer key.

## Architecture

```
┌─────────────────────┐       ┌──────────────────────────────────┐
│  React Frontend     │       │  Python Backend (FastAPI)         │
│  (Vite + Tailwind)  │──────▶│                                  │
│                     │  REST │  ┌────────────────────────────┐  │
│  • File upload UI   │       │  │  Provider Abstraction      │  │
│  • Step workflow    │       │  │  ┌────────┐ ┌──────────┐  │  │
│  • Results display  │       │  │  │ Gemini │ │  Claude  │  │  │
└─────────────────────┘       │  │  └────────┘ └──────────┘  │  │
                              │  │  ┌────────┐ ┌──────────┐  │  │
                              │  │  │  Qwen  │ │  Ollama  │  │  │
                              │  │  └────────┘ └──────────┘  │  │
                              │  └────────────────────────────┘  │
                              └──────────────────────────────────┘
```

## Technology Selection Rationale

### Frontend: React 19 + Vite + Tailwind CSS 4

- **React 19**: Latest stable release with improved performance and concurrent features. Widest ecosystem for file handling, state management, and future extensibility.
- **Vite**: Near-instant HMR, native ESM, and seamless TypeScript support. Orders of magnitude faster than webpack for development.
- **Tailwind CSS 4**: Utility-first approach eliminates CSS authoring overhead. V4 uses the new Vite plugin (no PostCSS config needed), native cascade layers, and significantly faster builds.

### Backend: Python + FastAPI

- **FastAPI**: Async-native, auto-generated OpenAPI docs, Pydantic validation. The de facto standard for ML/AI APIs due to Python's dominance in that space.
- **PyMuPDF (fitz)**: High-performance PDF rendering to images. Needed because vision models work on images, not raw PDF bytes.
- **Pillow**: Image validation and potential pre-processing (resize, normalize).

### AI Providers

| Provider | Mode | Why |
|----------|------|-----|
| **Gemini** (google-genai) | Cloud | Best-in-class multimodal (vision + reasoning). Native JSON output mode reduces parsing errors. Generous free tier. |
| **Claude** (anthropic) | Cloud | Exceptional at structured analysis and nuanced grading of open-ended answers. Strong vision capabilities. |
| **Qwen** (openai-compat) | Cloud | Competitive vision-language model. OpenAI-compatible API simplifies integration. Good alternative when Gemini/Claude quotas are exhausted. |
| **Ollama** | Local/Offline | Runs models like `qwen2.5-vl` entirely on-device. Zero data leaves the machine. Essential for privacy-sensitive educational environments and air-gapped deployments. |

### Why This Provider Set?

1. **Online-first, offline-capable**: Gemini and Claude provide the highest accuracy for complex exam structures. Ollama ensures the app works without internet.
2. **Unified interface**: All providers implement the same `BaseProvider` ABC, so switching between them is a single dropdown selection — no code changes.
3. **Vision-native**: All selected providers have first-class multimodal (image understanding) support, which is essential for reading handwritten or scanned exam documents.
4. **JSON-structured output**: Gemini supports native `response_mime_type="application/json"`, Claude and Qwen handle structured prompts well, and Ollama models increasingly support JSON mode.

## Quick Start

### Prerequisites

- Node.js 20+
- Python 3.11+
- (Optional) [Ollama](https://ollama.com) for local inference

### Root Scripts

```bash
# Start local MongoDB
npm run db:start

# Start backend API server
npm run dev:server
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Backend

```bash
cd backend
uv venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e .
cp .env.example .env
# Edit .env with your API keys
uv run uvicorn app.main:app --reload --port 8000
```

### Using Ollama (Offline Mode)

```bash
# Install Ollama from https://ollama.com
ollama pull qwen2.5-vl
# The backend auto-detects Ollama availability
```

### Docker Compose (One Command)

```bash
# Copy and configure environment
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys

# Run both frontend and backend
docker compose up --build
```

The app will be available at `http://localhost:3000`. The backend API runs on port 8000 internally.

## Running Tests

### Backend

```bash
cd backend
source .venv/bin/activate
pip install -e ".[dev]"
pytest -v
```

### Frontend

```bash
cd frontend
npm test
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/providers` | List available AI providers |
| POST | `/api/exam/template` | Upload empty exam for structure analysis |
| POST | `/api/exam/answer-key` | Upload exam with correct answers |
| POST | `/api/exam/grade` | Upload and grade student exams |

## Project Structure

```
├── frontend/           # React + Tailwind UI
│   └── src/
│       ├── components/ # Reusable UI components
│       ├── lib/        # API client
│       ├── test/       # Vitest component tests
│       └── App.tsx     # Main 3-step workflow
├── backend/            # Python FastAPI
│   ├── app/
│   │   ├── providers/  # AI provider implementations
│   │   ├── models/     # Pydantic data models
│   │   ├── file_processing.py
│   │   └── main.py     # API routes
│   └── tests/          # Pytest test suite
├── docs/
│   └── MODEL_TRAINING.md  # Guide for fine-tuning custom models
├── docker-compose.yml  # One-command deployment
└── README.md
```
