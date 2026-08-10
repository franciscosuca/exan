# Exan — AI Exam Scanner & Answer Comparator

An AI-powered application that scans exam documents, extracts their structure, and compares student responses with correct answers. Supports both cloud AI providers and fully offline local inference.

## How It Works

1. **Upload Empty Exam** — Upload a blank exam (PDF or image). The AI identifies all questions, their types, and point values.
2. **Upload Answer Key** — Upload the same exam filled in with correct answers.
3. **Compare Student Exams** — Upload one or more completed student exams. Each is compared automatically against the answer key.

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
                              │  │  │  GPT   │ │  Ollama  │  │  │
                              │  │  └────────┘ └──────────┘  │  │
                              │  │       ┌───────────┐        │  │
                              │  │       │ LM Studio │        │  │
                              │  │       └───────────┘        │  │
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
| **Claude** (anthropic) | Cloud | Exceptional at structured analysis and nuanced comparison of open-ended answers. Strong vision capabilities. |
| **GPT** (OpenAI) | Cloud | Strong multimodal document understanding through OpenAI's API. Uses the configurable `OPENAI_MODEL` setting. |
| **Ollama** | Local/Offline | Runs models like `qwen2.5-vl` entirely on-device. Zero data leaves the machine. Essential for privacy-sensitive educational environments and air-gapped deployments. |
| **LM Studio** | Local/Offline | Serves locally loaded vision models through an OpenAI-compatible API. Useful for selecting and testing local models through a desktop interface. |

### Why This Provider Set?

1. **Online-first, offline-capable**: Gemini, Claude, and GPT provide managed cloud inference. Ollama and LM Studio keep inference local when privacy or offline operation matters.
2. **Unified interface**: All providers implement the same `BaseProvider` ABC, so switching between them is a single dropdown selection — no code changes.
3. **Vision-native**: The cloud defaults and configured local models support image understanding, which is essential for reading handwritten or scanned exam documents.
4. **Consistent structured output**: Every provider receives the same JSON-focused prompts and returns data through the same parsing contract.

## Quick Start

### Prerequisites

- Bun 1.2+
- Node.js 20+ (for auth and release tooling)
- Python 3.11+
- (Optional) [Ollama](https://ollama.com) for local inference
- (Optional) [LM Studio](https://lmstudio.ai) for local inference

### Root Scripts

```bash
# Start local MongoDB
bun run db:start

# Start auth API server
bun run dev:auth
```

### Webapp

```bash
cd webapp
bun install
bun run dev
```

### Inference

```bash
cd inference
uv venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e .
cp .env.example .env
# Edit .env with your API keys
uv run uvicorn app.main:app --reload --port 8000
```

### Using Local Providers

#### Ollama

```bash
# Install Ollama from https://ollama.com
ollama pull qwen2.5-vl
# The inference service auto-detects Ollama availability
```

#### LM Studio

1. Install LM Studio from `https://lmstudio.ai` and load a vision-capable model.
2. Start its local server on port 1234.
3. Set `LMSTUDIO_MODEL` in `inference/.env` to the loaded model identifier.

Both local providers are reached through `localhost` during direct development and through `host.docker.internal` when the inference service runs in Docker Compose.

### Docker Compose (One Command)

```bash
# Copy and configure environment
cp inference/.env.example inference/.env
# Edit inference/.env with your API keys

# Run both webapp and inference services
docker compose up --build
```

The app will be available at `http://localhost:3000`. The inference API runs on port 8000 internally.

## Running Tests

### Inference

```bash
cd inference
source .venv/bin/activate
pip install -e ".[dev]"
pytest -v
```

### Webapp

```bash
cd webapp
bun run test
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/providers` | List available AI providers |
| POST | `/api/exam/template` | Upload empty exam for structure analysis |
| POST | `/api/exam/answer-key` | Upload exam with correct answers |
| POST | `/api/exam/compare` | Upload and compare student exams |

## Project Structure

```
├── webapp/             # React + Tailwind UI
│   └── src/
│       ├── components/ # Reusable UI components
│       ├── lib/        # API client
│       ├── test/       # Vitest component tests
│       └── App.tsx     # Main 3-step workflow
├── inference/          # Python FastAPI
│   ├── app/
│   │   ├── providers/  # AI provider implementations
│   │   ├── models/     # Pydantic data models
│   │   ├── utils/
│   │   │   ├── file_processing.py
│   │   │   └── run_logging.py
│   │   └── main.py      # App wiring and router registration
│   │   ├── api/         # Routers and dependency providers
│   │   ├── repositories/ # In-memory workflow state
│   │   ├── services/    # Workflow orchestration
│   └── tests/          # Pytest test suite
├── auth/               # Node/Express JWT auth microservice
├── db/                 # Mongo connection helper + init script
├── docs/
│   └── MODEL_TRAINING.md  # Guide for fine-tuning custom models
├── docker-compose.yml  # One-command deployment
└── README.md
```
