# Architecture Diagrams

This document contains Mermaid diagrams describing the Exan project architecture, workflows, and interactions.

---

## 1. High-Level Component Architecture

```mermaid
graph TB
    subgraph Frontend["Frontend (React 19 + Vite + Tailwind CSS 4)"]
        App["App.tsx<br/>(Mode Router)"]
        Landing["Landing Page"]
        Eval["ExamComparison / BatchEvaluation"]
        
        subgraph SharedComponents["Shared Components"]
            FD["FileDropzone"]
            PS["ProviderSelector"]
            SI["StepIndicator"]
        end
        
        subgraph ResultComponents["Result Components"]
            GR["GradingResults"]
            BR["BatchResults"]
        end
        
        API["api.ts<br/>(API Client)"]
    end
    
    subgraph Backend["Backend (Python FastAPI)"]
        Main["main.py<br/>(App Wiring)"]
        Routers["api/routes/<br/>(HTTP Routes)"]
        Services["services/<br/>(Workflow Orchestration)"]
        Repository["repositories/<br/>(In-Memory State)"]
        FP["file_processing.py<br/>(PDF/Word/Image)"]
        Models["models/<br/>(Pydantic Models)"]
        AI["AI-provider"]
    end

    App --> Landing
    App --> Eval
    Eval --> FD
    Eval --> PS
    Eval --> SI
    Eval --> GR
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
    API->>BE: POST /api/exam/template<br/>multipart: file, provider
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
    API->>BE: POST /api/exam/answer-key<br/>multipart: file, exam_id, provider
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
    API->>BE: POST /api/exam/grade<br/>multipart: files[], exam_id, provider
    BE->>PR: get_provider(provider)
    PR-->>BE: Provider instance
    loop For each student file
        BE->>BE: get_mime_type(filename, content_type)
        BE->>FP: process_upload(content, mime)
        FP-->>BE: Image bytes and MIME types
        BE->>AI: grade_exam(images, mimes, structure, key)
        AI-->>BE: Student name and answers
        BE->>BE: Calculate scores and percentage
    end
    BE->>LOG: write_run_log(exam-comparison, inputs, outputs, provider)
    BE-->>API: GradingResult[]
    API-->>EC: Store results and show breakdown
    EC-->>U: Display scores and per-question results
```

### 3.2 Batch Evaluation Flow

```mermaid
sequenceDiagram
    participant U as User
    participant BE as BatchEvaluation
    participant API as API Client
    participant SVC as FastAPI
    participant FP as File Processing
    participant PR as Provider Registry
    participant AI as AI Provider
    participant LOG as Run Logging

    U->>BE: Open Batch Evaluation
    BE->>API: getProviders()
    API->>SVC: GET /api/providers
    SVC->>PR: get_available_providers()
    PR-->>SVC: Provider status list
    SVC-->>API: ProviderConfig[]
    API-->>BE: Available providers

    U->>BE: Select provider and upload PDF/Word files
    U->>BE: Configure grammar and custom criteria
    U->>BE: Click Evaluate

    BE->>API: batchEvaluate(files, provider, language,<br/>includeGrammar, customCriteria)
    API->>SVC: POST /api/batch/evaluate<br/>multipart: files[], provider, language,<br/>include_grammar, custom_criteria JSON
    SVC->>SVC: Parse include_grammar and custom_criteria
    SVC->>PR: get_provider(provider)
    PR-->>SVC: Provider instance

    loop For each file
        SVC->>SVC: get_mime_type(filename, content_type)
        SVC->>FP: extract_text(content, mime)
        FP-->>SVC: Extracted document text

        opt Grammar enabled
            SVC->>SVC: grammar_evaluation_prompt(language)
            SVC->>AI: evaluate_text(text, grammar prompt)
            AI-->>BE: {score, feedback}
        end

        loop For each valid custom criterion
            SVC->>SVC: custom_criteria_evaluation_prompt(...)
            SVC->>AI: evaluate_text(text, criteria prompt)
            AI-->>SVC: {score, feedback}
        end

        SVC->>SVC: Calculate overall score and summary
    end

    SVC->>LOG: write_run_log(batch-evaluation, inputs, outputs, provider)
    SVC-->>API: BatchEvaluationResponse {id, results[], created_at}
    API-->>BE: Store response
    BE-->>U: Display per-file scores, breakdown, and feedback
```

---

## 4. Per-Feature Class Diagrams (PENDING TO READ)

TODO: This shall be simplified by removing the custom criteria and the grading-tools.

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
        +gradingResults: GradingResult[]
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
        +points: float
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
        +points: float
    }

    class GradingResult {
        +id: string
        +exam_id: string
        +student_name: string
        +filename: string
        +total_score: float
        +max_score: float
        +percentage: float
        +answers: StudentAnswer[]
    }

    class StudentAnswer {
        +question_number: int
        +student_answer: string
        +correct_answer: string
        +is_correct: bool
        +points_earned: float
        +points_possible: float
    }

    class BaseProvider_BE {
        <<abstract>>
        +name: string
        +analyze_exam_structure(images, mimes)*
        +extract_answers(images, mimes)*
        +grade_exam(images, mimes, structure, key)*
        +evaluate_text(text, prompt)*
    }

    class GeminiProvider_BE {
        +model: string
        +analyze_exam_structure()
        +extract_answers()
        +grade_exam()
        +evaluate_text()
    }

    App_FE --> ExamComparison_FE
    ExamComparison_FE --> ExamStructure
    ExamComparison_FE --> AnswerKey
    ExamComparison_FE --> GradingResult
    ExamStructure --> Question
    AnswerKey --> Answer
    GradingResult --> StudentAnswer
    BaseProvider_BE <|-- GeminiProvider_BE
```

### 4.2 Batch Evaluation — Models & Classes

```mermaid
classDiagram
    direction TB

    class BatchEvaluation_FE {
        +providers: ProviderConfig[]
        +selectedProvider: string
        +files: File[]
        +language: string
        +includeGrammar: boolean
        +customCriteria: EvaluationCriteria[]
        +results: BatchEvaluationResponse
        +handleFiles(files)
        +handleEvaluate()
        +addCriteria()
        +updateCriteria(index, field, value)
        +removeCriteria(index)
        +reset()
    }

    class EvaluationCriteria {
        +name: string
        +description: string
        +zero_description: string
        +hundred_description: string
    }

    class BatchEvaluationResponse {
        +id: string
        +results: FileEvaluationResult[]
        +created_at: string
    }

    class FileEvaluationResult {
        +id: string
        +filename: string
        +scores: CriteriaScore[]
        +overall_score: float
        +summary: string
    }

    class CriteriaScore {
        +criteria_name: string
        +score: float
        +feedback: string
    }

    class BatchResults_FE {
        +response: BatchEvaluationResponse
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
        +custom_criteria_evaluation_prompt(name, desc, zero, hundred) string
    }

    BatchEvaluation_FE --> EvaluationCriteria
    BatchEvaluation_FE --> BatchEvaluationResponse
    BatchEvaluationResponse --> FileEvaluationResult
    FileEvaluationResult --> CriteriaScore
    BatchResults_FE --> BatchEvaluationResponse
    BaseProvider_BE ..> prompts_BE : uses prompts
    file_processing_BE ..> BaseProvider_BE : provides text to
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
        +grade_exam(images, mimes, structure, key)* dict
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
