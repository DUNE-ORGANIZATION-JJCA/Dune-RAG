# Evaluation Dataset

This directory contains the evaluation dataset and scripts for measuring RAG quality.

## Files

- `sample_dataset.json` - Default evaluation dataset with Q&A pairs
- `eval_dataset.py` - CLI tool to manage the dataset
- `README.md` - This file

## Usage

### Adding Questions

```bash
# Add a new Q&A pair
python data/eval/eval_dataset.py add \
  "¿Cómo se gana el juego?" \
  "Se gana acumulando suficientes puntos de victoria mediante..."

# Add with difficulty level
python data/eval/eval_dataset.py add \
  "¿Qué ventajas tiene House Atreides?" \
  "Los Atreides tienen bonificaciones en comercio..." \
  --difficulty easy
```

### Listing Questions

```bash
python data/eval/eval_dataset.py list
```

### Removing Questions

```bash
python data/eval/eval_dataset.py remove q1
```

### Running Evaluation

```bash
# Full evaluation with Ragas
python scripts/run_eval.py --dataset data/eval/sample_dataset.json

# Skip Ragas (basic evaluation)
python scripts/run_eval.py --dataset data/eval/sample_dataset.json --skip-ragas

# Custom output
python scripts/run_eval.py --output data/eval/my_results.json
```

## Quality Metrics

| Metric | Threshold | Description |
|--------|-----------|-------------|
| Faithfulness | 0.50 | Percentage of claims verifiable from context |
| Answer Relevancy | 0.60 | How relevant the answer is to the question |
| Context Precision | 0.50 | Quality of retrieved context |
| Context Recall | 0.60 | Coverage of ground truth in context |

## Dataset Format

```json
{
  "id": "q1",
  "question": "The question text",
  "ground_truth": "The expected answer",
  "expected_sources": ["source1", "source2"],
  "difficulty": "easy|medium|hard"
}
```

## Recommendations

- Start with 5-10 questions covering different aspects
- Include easy, medium, and hard questions
- Update the dataset as you improve the RAG
- Run evaluation after major changes