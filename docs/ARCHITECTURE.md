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
        Main["main.py<br/>(API Routes)"]
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
    
    API -->|HTTP REST| Main
    Main --> FP
    Main --> Models
    Main --> AI
```

---

## 2. User Workflow Diagrams

### 2.1 Landing Page Selection

```mermaid
flowchart TD
    Start([User opens Exan]) --> Landing{Landing Page}
    Landing -->|"Exam Comparison"| EC[Exam Comparison Workflow]
    Landing -->|"Batch Evaluation"| BE[Batch Evaluation Workflow]
    EC --> BackEC[← Back to Landing]
    BE --> BackBE[← Back to Landing]
    BackEC --> Landing
    BackBE --> Landing
```

### 2.2 Exam Comparison Workflow

```mermaid
flowchart TD
    Start([Enter Exam Comparison]) --> SelectProvider[Select AI Provider]
    SelectProvider --> Step1[Step 1: Upload Exam Template]
    Step1 -->|PDF/Image| Analyze[AI Analyzes Structure]
    Analyze --> ShowQuestions[Show detected questions count]
    ShowQuestions --> Step2[Step 2: Upload Answer Key]
    Step2 -->|PDF/Image| Extract[AI Extracts Answers]
    Extract --> ShowAnswers[Show loaded answers count]
    ShowAnswers --> Step3[Step 3: Upload Student Exams]
    Step3 -->|Multiple PDF/Images| Grade[AI Grades Each Exam]
    Grade --> Results[Show Grading Results]
    Results --> Details[View per-question breakdown]
    Results --> Reset[Start Over]
    Reset --> Step1
```

### 2.3 Batch Evaluation Workflow

```mermaid
flowchart TD
    Start([Enter Batch Evaluation]) --> SelectProvider[Select AI Provider]
    SelectProvider --> Upload[Upload Exam Files<br/>PDF or Word, multiple]
    Upload --> ConfigCriteria{Configure Criteria}
    
    ConfigCriteria --> Grammar[Enable Grammar Check<br/>+ select language]
    ConfigCriteria --> Custom[Add Custom Criteria<br/>name + description +<br/>0% definition + 100% definition]
    ConfigCriteria --> AddMore[Add More Custom Criteria]
    AddMore --> Custom
    
    Grammar --> Evaluate[Click Evaluate]
    Custom --> Evaluate
    
    Evaluate --> Processing[AI evaluates each file<br/>against each criteria]
    Processing --> Results[Show Results:<br/>per-file scores, per-criteria breakdown,<br/>overall percentage, feedback]
    Results --> NewEval[New Evaluation]
    NewEval --> Upload
```

---

## 3. Swimlane Diagram — Frontend / Backend Interaction

### 3.1 Exam Comparison Flow

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant BE as Backend API
    participant AI as AI Provider

    U->>FE: Open app
    FE->>BE: GET /api/providers
    BE-->>FE: List of available providers

    U->>FE: Select provider
    U->>FE: Upload exam template (PDF/Image)
    FE->>BE: POST /api/exam/template<br/>{file, provider}
    BE->>BE: process_upload() → images
    BE->>AI: analyze_exam_structure(images)
    AI-->>BE: {questions: [...]}
    BE-->>FE: ExamStructure {id, questions}

    U->>FE: Upload answer key (PDF/Image)
    FE->>BE: POST /api/exam/answer-key<br/>{file, exam_id, provider}
    BE->>BE: process_upload() → images
    BE->>AI: extract_answers(images)
    AI-->>BE: {answers: [...]}
    BE-->>FE: AnswerKey {id, answers}

    U->>FE: Upload student exams (multiple)
    FE->>BE: POST /api/exam/grade<br/>{files[], exam_id, provider}
    loop For each student file
        BE->>BE: process_upload() → images
        BE->>AI: grade_exam(images, structure, key)
        AI-->>BE: {student_name, answers}
    end
    BE-->>FE: GradingResult[]
    FE->>U: Display scores & breakdown
```

### 3.2 Batch Evaluation Flow

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant BE as Backend API
    participant AI as AI Provider

    U->>FE: Open app → Batch Evaluation
    FE->>BE: GET /api/providers
    BE-->>FE: List of available providers

    U->>FE: Select provider
    U->>FE: Upload files (PDF/Word)
    U->>FE: Configure criteria<br/>(grammar + custom)
    U->>FE: Click "Evaluate"

    FE->>BE: POST /api/batch/evaluate<br/>{files[], provider, language,<br/>include_grammar, custom_criteria}

    loop For each file
        BE->>BE: extract_text(file) → text

        opt Grammar enabled
            BE->>AI: evaluate_text(text, grammar_prompt)
            AI-->>BE: {score, feedback}
        end

        loop For each custom criteria
            BE->>AI: evaluate_text(text, criteria_prompt)
            AI-->>BE: {score, feedback}
        end

        BE->>BE: Calculate overall score
    end

    BE-->>FE: BatchEvaluationResponse {results[]}
    FE->>U: Display per-file scores,<br/>per-criteria breakdown & feedback
```

---

## 4. Per-Feature Class Diagrams

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
