# FinBot — RAGAs Evaluation Results

## RAGAs Ablation Study Results

| Configuration | Faithfulness | Context Precision | Context Recall | 
|---|---|---|---|
| Baseline RAG (no routing, no guardrails) | 0.07000 | 0.6000 | 0.8000 |
| Full System (routing + RBAC + guardrails) | 0.6000 | 0.5000 | 0.7000 |

*Evaluated on 5 samples per configuration.*

## Notes

- Evaluation run against 40 ground truth QA pairs
- Judge LLM: Groq Llama 3.1 8B
- Scores range 0-1, higher is better
