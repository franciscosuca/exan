# Model Training Guide — Teaching AI to Grade Exams

This document explains how to fine-tune or train a custom model specifically for understanding exam structures, recognizing handwritten answers, and determining correctness. This is a future enhancement for when you want higher accuracy than generic vision-language models provide out of the box.

---

## 1. Why Train a Custom Model?

General-purpose models (Gemini, Claude, Qwen) are good at understanding documents, but they:

- May misread certain handwriting styles common in your student population
- Don't know your specific grading rubrics (partial credit rules, acceptable variations)
- Can't learn from corrections you make over time
- May struggle with domain-specific notation (math formulas, chemical equations, musical notation)

A fine-tuned model addresses all of these by learning from your historical exam data.

---

## 2. Training Data Requirements

### 2.1 Dataset Structure

You need three types of labeled data:

```
training_data/
├── exam_structures/        # Labeled exam templates
│   ├── exam_001.png
│   ├── exam_001.json       # Ground-truth structure annotation
│   └── ...
├── answer_keys/            # Correct answer annotations
│   ├── key_001.png
│   ├── key_001.json        # Ground-truth answers
│   └── ...
└── graded_exams/           # Student exams with human-verified grades
    ├── student_001_exam_001.png
    ├── student_001_exam_001.json  # Human-verified grading
    └── ...
```

### 2.2 Annotation Format

**Exam Structure** (`exam_001.json`):
```json
{
  "questions": [
    {
      "number": 1,
      "text": "What is the derivative of x²?",
      "type": "open_ended",
      "points": 5,
      "bounding_box": [x1, y1, x2, y2]
    }
  ]
}
```

**Graded Exam** (`student_001_exam_001.json`):
```json
{
  "student_name": "Maria García",
  "answers": [
    {
      "question_number": 1,
      "student_answer": "2x",
      "is_correct": true,
      "points_earned": 5,
      "points_possible": 5,
      "grader_notes": "Correct application of power rule"
    }
  ]
}
```

### 2.3 Recommended Dataset Size

| Task | Minimum | Recommended |
|------|---------|-------------|
| Exam structure detection | 50 exams | 200+ exams |
| Handwriting recognition | 500 answers | 2000+ answers |
| Grading accuracy | 200 graded exams | 1000+ graded exams |

---

## 3. Training Approaches

### 3.1 Fine-Tuning a Vision-Language Model (Recommended)

This is the most practical approach. You take an existing multimodal model and teach it your specific exam formats.

**Best base models for fine-tuning:**

| Model | Why | How |
|-------|-----|-----|
| **Qwen2.5-VL (7B/72B)** | Open weights, excellent vision, runs locally via Ollama | LoRA/QLoRA fine-tuning |
| **PaliGemma 2** | Google's open vision-language model, small & efficient | Full or LoRA fine-tune via HuggingFace |
| **LLaVA-Next** | Strong document understanding, open source | LoRA with LLaVA training scripts |

**Framework: Unsloth or HuggingFace TRL**

```bash
pip install unsloth trl datasets
```

```python
from unsloth import FastVisionModel
from trl import SFTTrainer, SFTConfig
from datasets import load_dataset

# Load base model
model, tokenizer = FastVisionModel.from_pretrained(
    "unsloth/Qwen2.5-VL-7B-Instruct",
    load_in_4bit=True,
)

# Apply LoRA adapters (only trains ~1-5% of params)
model = FastVisionModel.get_peft_model(
    model,
    r=16,
    lora_alpha=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
)

# Load your exam dataset
dataset = load_dataset("json", data_files="training_data/train.jsonl")

# Train
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset["train"],
    args=SFTConfig(
        output_dir="./exan-model",
        num_train_epochs=3,
        per_device_train_batch_size=2,
        learning_rate=2e-4,
    ),
)
trainer.train()

# Save adapter weights
model.save_pretrained("./exan-model-lora")
```

### 3.2 Training Data Format for Fine-Tuning

Create a JSONL file where each line is a conversation:

```jsonl
{"messages": [{"role": "user", "content": [{"type": "image", "image": "exam_001.png"}, {"type": "text", "text": "Analyze this exam and identify all questions. Return JSON."}]}, {"role": "assistant", "content": "{\"questions\": [{\"number\": 1, ...}]}"}]}
{"messages": [{"role": "user", "content": [{"type": "image", "image": "student_001.png"}, {"type": "text", "text": "Grade this exam. The answer key is: ..."}]}, {"role": "assistant", "content": "{\"student_name\": \"Maria\", \"answers\": [...]}"}]}
```

### 3.3 Deploying the Fine-Tuned Model

After training, you have LoRA adapter weights. To use them:

**Option A: Merge into Ollama (recommended for production)**

```bash
# Merge LoRA weights with base model
python merge_lora.py --base Qwen2.5-VL-7B --lora ./exan-model-lora --output ./exan-model-merged

# Create Ollama Modelfile
cat > Modelfile <<EOF
FROM ./exan-model-merged
PARAMETER temperature 0.1
SYSTEM "You are an expert exam grader. Always respond with valid JSON."
EOF

# Import into Ollama
ollama create exan-grader -f Modelfile
```

Then update `.env`:
```
OLLAMA_MODEL=exan-grader
```

**Option B: Serve via vLLM (for higher throughput)**

```bash
pip install vllm
vllm serve ./exan-model-merged --port 8001
```

---

## 4. Iterative Improvement Loop

The most effective training process is iterative:

```
┌─────────────────────────────────────────────┐
│                                             │
│  1. Grade exams with current model          │
│          ↓                                  │
│  2. Teacher reviews & corrects grades       │
│          ↓                                  │
│  3. Corrections become training data        │
│          ↓                                  │
│  4. Re-train model with new data            │
│          ↓                                  │
│  5. Deploy updated model → back to step 1   │
│                                             │
└─────────────────────────────────────────────┘
```

### 4.1 Implementing Feedback Collection

Add a "correction" endpoint to the inference service:

```python
@app.post("/api/exam/correct")
async def submit_correction(
    result_id: str,
    corrections: list[dict],  # [{question_number, correct_grade, notes}]
):
    # Store corrections as new training data
    save_to_training_set(result_id, corrections)
```

### 4.2 When to Re-Train

- After collecting 50+ corrections
- When accuracy drops below your threshold (e.g., <90%)
- When introducing a new exam format or question type
- At the start of each academic term

---

## 5. Hardware Requirements

| Approach | GPU VRAM | Training Time (1000 samples) |
|----------|----------|------------------------------|
| QLoRA 7B model | 8 GB | ~2 hours |
| LoRA 7B model | 16 GB | ~1.5 hours |
| Full fine-tune 7B | 48 GB | ~4 hours |
| QLoRA 72B model | 24 GB | ~8 hours |

**Recommended setup for a school/university:**
- 1x NVIDIA RTX 4090 (24 GB) — handles LoRA training and local inference
- Or: Use cloud GPUs (RunPod, Lambda, Google Colab Pro) for training, deploy locally for inference

---

## 6. Evaluation & Metrics

Track these metrics to measure model improvement:

| Metric | Description | Target |
|--------|-------------|--------|
| Structure Detection Accuracy | % of questions correctly identified | >95% |
| Answer Extraction Accuracy | % of answers correctly read | >90% |
| Grading Accuracy | % of grades matching human grader | >85% |
| Partial Credit Agreement | Correlation with human partial credit | >0.8 |

### 6.1 Evaluation Script

```python
def evaluate_model(test_set, model):
    correct = 0
    total = 0
    for exam in test_set:
        predicted = model.grade(exam.image)
        for pred, truth in zip(predicted.answers, exam.ground_truth):
            total += 1
            if pred.is_correct == truth.is_correct:
                correct += 1
    return correct / total
```

---

## 7. Summary of Recommended Path

1. **Start with zero-shot** (current implementation) — use Gemini/Claude/Qwen as-is
2. **Collect corrections** — have teachers verify and correct AI grades
3. **Fine-tune Qwen2.5-VL-7B with LoRA** — using 200+ corrected examples
4. **Deploy via Ollama** — keeps everything local and fast
5. **Iterate** — continuously improve with new corrections each term

This approach gives you the best accuracy trajectory while keeping costs low and maintaining full data privacy through local inference.
