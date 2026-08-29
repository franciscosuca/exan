# Exan Architecture

This document is the short architecture index for Exan. It keeps the project purpose, current implementation status, architecture decisions, and links to deeper technical details in one place.

## Table of Contents

- [Purpose](#purpose)
- [Current Status](#current-status)
- [Architecture Options](#architecture-options)
- [Recommended Architecture](#recommended-architecture)
    - [Service boundaries](#service-boundaries)
    - [Request flow](#request-flow)
    - [Provider abstraction](#provider-abstraction)
    - [State and persistence](#state-and-persistence)
    - [Authentication and security](#authentication-and-security)
- [Detailed Architecture Diagrams](#detailed-architecture-diagrams)
    - [High-level component architecture](#1-high-level-component-architecture)
    - [Frontend and backend interaction](#3-swimlane-diagram--frontend--backend-interaction)
    - [Per-feature class diagrams](#4-per-feature-class-diagrams-pending-to-read)

## Purpose

Exan scans exam documents, extracts their structure, and compares student responses with correct answers using AI. The architecture supports both cloud providers and local inference while keeping the frontend workflow consistent across providers.

## Current Status

- The React 19 webapp provides Exam Comparison and Grammar Evaluation workflows.
- The FastAPI inference service owns document processing, workflow orchestration, provider selection, and answer comparison.
- Gemini, Claude, GPT, Ollama, and LM Studio are represented behind a shared provider abstraction.
- Express and MongoDB provide authentication and user storage.
- Exam and answer-key workflow state is currently held in FastAPI process memory.
- Inference endpoints are not yet authenticated, so user ownership and provider-credential isolation are not complete.
- Docker Compose runs the webapp, inference service, auth service, and MongoDB for local deployment.

## Architecture Options

The options and their subtopics are maintained separately so this index remains quick to scan:

- [Architecture options and trade-offs](architecture/ARCHITECTURE_OPTIONS.md): service topology, runtime provider credentials, phone scanning, storage, and deployment choices.
- [Runtime provider, credential, model, and effort selection](PROVIDER_RUNTIME.md): detailed provider-connection alternatives and API contract.
- [Phone scanning integration options](scanning/SCANNING_INTEGRATION_OPTIONS.md): mobile capture and desktop handoff alternatives.
- [First release deployment options](deployment/DEPLOYMENT_OPTIONS.md): hosting platform comparison, container-versus-Kubernetes topology, and infrastructure automation for the beta deployment.

## Recommended Architecture

### Service boundaries

- **Webapp:** React UI, upload workflows, provider selection, and result presentation.
- **Inference:** FastAPI routes, document processing, workflow services, repositories, provider registry, and AI calls.
- **Auth:** Express JWT issuance and identity ownership.
- **Database:** MongoDB user persistence and future durable metadata.
- **Reverse proxy:** nginx routes `/api/auth/*` to `auth-server` and other `/api/*` requests to `inference`.

### Request flow

The browser submits files and workflow settings to FastAPI. FastAPI validates the request, processes files into text or images, resolves a provider through the registry, invokes the model, normalizes the structured result, and returns it to the React workflow. The detailed sequence diagrams below document the current flows.

### Provider abstraction

All providers implement the shared `BaseProvider` contract. The registry exposes provider availability and returns the selected implementation, allowing cloud and local providers to share the same exam-analysis and text-evaluation workflows. Runtime model and credential selection is documented in [PROVIDER_RUNTIME.md](PROVIDER_RUNTIME.md).

### State and persistence

Keep the current in-memory repositories for the single-instance MVP. Before adding multiple inference replicas or durable workflows, move workflow state to a shared persistence layer with explicit user ownership. Temporary uploads and runtime provider connections should have bounded lifetimes and cleanup.

### Authentication and security

Authenticate every inference endpoint using the authenticated Exan user, bind exams and answer keys to that user, and avoid returning raw upstream provider errors. For runtime credentials, use the short-lived server-side provider connection described in [PROVIDER_RUNTIME.md](PROVIDER_RUNTIME.md); never return or log the credential.

## Detailed Architecture Diagrams

The following sections retain the implementation diagrams and are intentionally lower in the document. Use the table of contents for direct navigation.

---

## 1. High-Level Component Architecture

```mermaid
graph TB
    subgraph Frontend["Frontend (React 19 + Vite + Tailwind CSS 4)"]
        App["App.tsx<br/>(Mode Router)"]
        Landing["Landing Page"]
        Eval["ExamComparison / GrammarEvaluation"]
        
        subgraph SharedComponents["Shared Components"]
            FD["FileDropzone"]
            PS["ProviderSelector"]
            SI["StepIndicator"]
        end
        
        subgraph ResultComponents["Result Components"]
            CR["ComparisonResults"]
            BR["GrammarResults"]
        end
        
        API["api.ts<br/>(API Client)"]
    end
    
    subgraph Backend["Backend (Python FastAPI)"]
        Main["main.py<br/>(App Wiring)"]
        Routers["api/routes/<br/>(HTTP Routes)"]
        Services["services/<br/>(Workflow Orchestration)"]
        Repository["repositories/<br/>(In-Memory State)"]
        FP["file_processing.py<br/>(PDF/Word/Image)"]
        Models["models/<domain>.py<br/>(Pydantic Models)"]
        AI["AI-provider"]
    end

    App --> Landing
    App --> Eval
    Eval --> FD
    Eval --> PS
    Eval --> SI
    Eval --> CR
    Eval --> BR
    Eval --> API
    
    API -->|HTTP REST| Routers
    Main --> Routers
    Routers --> Services
    Services --> Repository
    Services --> FP
    Services --> Models
    Services --> AI
```

---

## 3. Swimlane Diagram — Frontend / Backend Interaction

### 3.1 Exam Comparison Flow

```mermaid
sequenceDiagram
    participant U as User
    participant EC as ExamComparison
    participant API as API Client
    participant BE as FastAPI
    participant FP as File Processing
    participant PR as Provider Registry
    participant AI as AI Provider
    participant LOG as Run Logging

    U->>EC: Open Exam Comparison
    EC->>API: getProviders()
    API->>BE: GET /api/providers
    BE->>PR: get_available_providers()
    PR-->>BE: Provider status list
    BE-->>API: ProviderConfig[]
    API-->>EC: Available providers

    U->>EC: Select provider and upload template
    EC->>API: uploadExamTemplate(file, provider)
    API->>BE: POST /api/exam-comparison/template<br/>multipart: file, provider
    BE->>BE: get_mime_type(filename, content_type)
    BE->>FP: process_upload(content, mime)
    FP-->>BE: Image bytes and MIME types
    BE->>PR: get_provider(provider)
    PR-->>BE: Provider instance
    BE->>AI: analyze_exam_structure(images, mimes)
    AI-->>BE: Raw structure with questions
    BE-->>API: ExamStructure {id, filename, questions, created_at}
    API-->>EC: Store exam structure and advance step

    U->>EC: Upload answer key
    EC->>API: uploadAnswerKey(file, exam_id, provider)
    API->>BE: POST /api/exam-comparison/answer-key<br/>multipart: file, exam_id, provider
    BE->>BE: Validate exam_id and get_mime_type()
    BE->>FP: process_upload(content, mime)
    FP-->>BE: Image bytes and MIME types
    BE->>PR: get_provider(provider)
    PR-->>BE: Provider instance
    BE->>AI: extract_answers(images, mimes)
    AI-->>BE: Raw answers
    BE->>BE: Normalize answer fields and store answer key
    BE-->>API: AnswerKey {id, exam_id, answers, created_at}
    API-->>EC: Store answer key and advance step

    U->>EC: Upload one or more student exams
    EC->>API: uploadStudentExams(files, exam_id, provider)
    API->>BE: POST /api/exam-comparison/compare<br/>multipart: files[], exam_id, provider
    BE->>PR: get_provider(provider)
    PR-->>BE: Provider instance
    loop For each student file
        BE->>BE: get_mime_type(filename, content_type)
        BE->>FP: process_upload(content, mime)
        FP-->>BE: Image bytes and MIME types
        BE->>AI: compare_exam(images, mimes, structure, key)
        AI-->>BE: Student name and answers
    end
    BE->>LOG: write_run_log(exam-comparison, inputs, outputs, provider)
    BE-->>API: ComparisonResult[]
    API-->>EC: Store results and show answer comparison
    EC-->>U: Display correct and incorrect answers
```

### 3.2 Grammar Evaluation Flow

```mermaid
sequenceDiagram
    participant U as User
    participant BE as GrammarEvaluation
    participant API as API Client
    participant SVC as FastAPI
    participant FP as File Processing
    participant PR as Provider Registry
    participant AI as AI Provider
    participant LOG as Run Logging

    U->>BE: Open Grammar Evaluation
    BE->>API: getProviders()
    API->>SVC: GET /api/providers
    SVC->>PR: get_available_providers()
    PR-->>SVC: Provider status list
    SVC-->>API: ProviderConfig[]
    API-->>BE: Available providers

    U->>BE: Select provider and upload PDF/Word files
    U->>BE: Select grammar feedback language
    U->>BE: Click Evaluate

    BE->>API: grammarEvaluate(files, provider, language)
    API->>SVC: POST /api/grammar-evaluation/evaluate<br/>multipart: files[], provider, language
    SVC->>PR: get_provider(provider)
    PR-->>SVC: Provider instance

    loop For each file
        SVC->>SVC: get_mime_type(filename, content_type)
        SVC->>FP: extract_text(content, mime)
        FP-->>SVC: Extracted document text

        SVC->>SVC: grammar_evaluation_prompt(language)
        SVC->>AI: evaluate_text(text, grammar prompt)
        AI-->>SVC: {grammar: {issues[], summary}}
        SVC->>SVC: Use grammar summary for the top-level summary
    end

    SVC->>LOG: write_run_log(grammar-evaluation, inputs, outputs, provider)
    SVC-->>API: GrammarEvaluationResponse {id, results[], created_at}
    API-->>BE: Store response
    BE-->>U: Display per-file grammar findings and summary
```

---

## 4. Per-Feature Class Diagrams (PENDING TO READ)

Grammar Evaluation is grammar-only; the remaining diagrams describe the active
response contract and shared comparison infrastructure.

### 4.1 Exam Comparison — Models & Classes

```mermaid
classDiagram
    direction TB

    class App_FE {
        +mode: AppMode
        +setMode()
    }

    class ExamComparison_FE {
        +providers: ProviderConfig[]
        +selectedProvider: string
        +currentStep: number
        +examStructure: ExamStructure
        +answerKey: AnswerKey
        +comparisonResults: ComparisonResult[]
        +handleExamTemplate(files)
        +handleAnswerKey(files)
        +handleStudentExams(files)
        +reset()
    }

    class ExamStructure {
        +id: string
        +filename: string
        +questions: Question[]
        +created_at: string
    }

    class Question {
        +number: int
        +text: string
        +type: string
        +options: string[]
    }

    class AnswerKey {
        +id: string
        +exam_id: string
        +answers: Answer[]
        +created_at: string
    }

    class Answer {
        +question_number: int
        +correct_answer: string
    }

    class ComparisonResult {
        +id: string
        +exam_id: string
        +student_name: string
        +filename: string
        +answers: StudentAnswer[]
    }

    class StudentAnswer {
        +question_number: int
        +student_answer: string
        +correct_answer: string
        +is_correct: bool
    }

    class BaseProvider_BE {
        <<abstract>>
        +name: string
        +analyze_exam_structure(images, mimes)*
        +extract_answers(images, mimes)*
        +compare_exam(images, mimes, structure, key)*
        +evaluate_text(text, prompt)*
    }

    class GeminiProvider_BE {
        +model: string
        +analyze_exam_structure()
        +extract_answers()
        +compare_exam()
        +evaluate_text()
    }

    App_FE --> ExamComparison_FE
    ExamComparison_FE --> ExamStructure
    ExamComparison_FE --> AnswerKey
    ExamComparison_FE --> ComparisonResult
    ExamStructure --> Question
    AnswerKey --> Answer
    ComparisonResult --> StudentAnswer
    BaseProvider_BE <|-- GeminiProvider_BE
```

### 4.2 Grammar Evaluation — Models & Classes

```mermaid
classDiagram
    direction TB

    class GrammarEvaluation_FE {
        +providers: ProviderConfig[]
        +selectedProvider: string
        +files: File[]
        +language: string
        +results: GrammarEvaluationResponse
        +handleFiles(files)
        +handleEvaluate()
        +reset()
    }

    class GrammarEvaluationResponse {
        +id: string
        +results: FileEvaluationResult[]
        +created_at: string
    }

    class FileEvaluationResult {
        +id: string
        +filename: string
        +summary: string
        +grammar: GrammarFeedback | null
    }

    class GrammarFeedback {
        +issues: GrammarIssue[]
        +summary: string
    }

    class GrammarIssue {
        +original_text: string
        +corrected_text: string
    }

    class GrammarResults_FE {
        +response: GrammarEvaluationResponse
    }

    class BaseProvider_BE {
        <<abstract>>
        +evaluate_text(text, prompt)*
    }

    class file_processing_BE {
        +extract_text(bytes, mime) string
        +extract_text_from_pdf(bytes) string
        +extract_text_from_word(bytes) string
        +get_mime_type(filename, content_type) string
    }

    class prompts_BE {
        +grammar_evaluation_prompt(language) string
    }

    GrammarEvaluation_FE --> GrammarEvaluationResponse
    GrammarEvaluationResponse --> FileEvaluationResult
    FileEvaluationResult --> GrammarFeedback
    GrammarFeedback --> GrammarIssue
    GrammarResults_FE --> GrammarEvaluationResponse
    BaseProvider_BE --> prompts_BE : uses prompts
    file_processing_BE --> BaseProvider_BE : provides text to
```

### 4.3 Shared Infrastructure — Provider Registry

```mermaid
classDiagram
    direction TB

    class BaseProvider {
        <<abstract>>
        +name: string
        +analyze_exam_structure(images, mimes)* dict
        +extract_answers(images, mimes)* dict
        +compare_exam(images, mimes, structure, key)* dict
        +evaluate_text(text, prompt)* dict
    }

    class GeminiProvider {
        +model: "gemini-2.5-flash"
        -_client: genai.Client
        -_build_content(images, mimes, prompt)
        -_parse_json(text) dict
    }

    class ClaudeProvider {
        +model: "claude-sonnet-4-20250514"
        +client: anthropic.Anthropic
        -_build_content(images, mimes, prompt)
        -_parse_json(text) dict
    }

    class OpenAICompatibleProvider {
        +model: string
        -_client: OpenAI
        -_build_content(images, mimes, prompt)
        -_parse_json(text) dict
    }

    class GPTProvider {
        +model: "gpt-4o-mini"
    }

    class LMStudioProvider {
        +model: string
        +base_url: "http://localhost:1234/v1"
    }

    class OllamaProvider {
        +model: string
        +base_url: string
        -_build_messages(images, mimes, prompt)
        -_chat(messages) string
        -_parse_json(text) dict
    }

    class Registry {
        +get_provider(name) BaseProvider
        +get_available_providers() list
    }

    class ProviderConfig {
        +provider: string
        +available: bool
        +requires_api_key: bool
        +is_local: bool
    }

    BaseProvider <|-- GeminiProvider
    BaseProvider <|-- ClaudeProvider
    BaseProvider <|-- OpenAICompatibleProvider
    OpenAICompatibleProvider <|-- GPTProvider
    OpenAICompatibleProvider <|-- LMStudioProvider
    BaseProvider <|-- OllamaProvider
    Registry --> BaseProvider
    Registry --> ProviderConfig
```
