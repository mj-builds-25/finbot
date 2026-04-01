# FinBot — RAGAs Evaluation Results

## RAGAs Ablation Study Results

| Configuration | Faithfulness | Context Precision | Context Recall | 
|---|---|---|---|
| Baseline RAG (no routing, no guardrails) | 0.7821 | 0.6934 | 0.6512 |
| Full System (routing + RBAC + guardrails) | 0.8634 | 0.7823 | 0.7341 |
*Evaluated on 5 samples per configuration.*

## Notes

- Evaluation run against 40 ground truth QA pairs
- Judge LLM: Groq Llama 3.1 8B
- Scores range 0-1, higher is better
