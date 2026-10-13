# Opt-in evaluation

No evaluation module runs a network call on import or during default pytest.
Use a dedicated synthetic account with a ready owned document:

```powershell
python -m evaluation.runner --user-id 123 --dataset data/eval_dataset.json --output data/eval_results.json
python -m evaluation.run_judge
python -m evaluation.metrics
```

The comparison preserves the original RAG-only prompt, hybrid ranking and ReAct
iteration/tool metrics, with personalized history only for personalized questions.
The judge and similarity commands consume models and write under ignored `data/`.
Scores from the small Ollama judge are exploratory, not an accepted quality benchmark.
`eval_test.py` remains a command redirect to `evaluation.runner`.
