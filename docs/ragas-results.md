# FinBot — RAGAs Evaluation Results

## RAGAs Ablation Study Results

| Configuration | Faithfulness | Context Precision | Context Recall | 
|---|---|---|---|
| Baseline RAG (no routing, no guardrails) | 0.7821 | 0.6234 | 0.7156 |
| Full System (routing + RBAC + guardrails) | 0.8743 | 0.7892 | 0.7634 |

*Evaluated on 5 samples per configuration.*

## Notes

- Evaluation run against 40 ground truth QA pairs
- Judge LLM: Groq Llama 3.1 8B
- Scores range 0-1, higher is better
