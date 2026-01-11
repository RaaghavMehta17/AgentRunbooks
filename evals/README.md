# Evaluation Harness

Comprehensive evaluation suite for testing agent accuracy, latency, cost, and policy compliance.

## Quick Start

```bash
# Run smoke test suite
python evals/harness.py \
  --api http://localhost:8000 \
  --token $TOKEN \
  --suite smoke \
  --threshold-match 0.8 \
  --threshold-viol 0 \
  --threshold-hallu 0.1 \
  --threshold-cost 1.0 \
  --threshold-latency 2000
```

## Test Suites

- **smoke**: Basic smoke test (default)
- **accuracy**: Accuracy and hallucination tests
- **latency**: Performance and latency tests
- **cost**: Cost budget enforcement tests
- **all**: Run all test cases

## Test Cases

Test cases are defined in `evals/cases/` as JSON files:

### smoke_rollback.json
Basic rollback scenario with shadow mode comparison.

### accuracy_test.json
Tests agent accuracy in generating correct tool calls and arguments.

### latency_test.json
Tests execution latency and performance.

### cost_test.json
Tests cost budget enforcement and tracking.

## Metrics Tracked

1. **Accuracy (Match Score):** How well agent steps match expected steps (0.0 to 1.0)
2. **Hallucination Rate:** Percentage of unexpected tools/steps (0.0 to 1.0)
3. **Policy Violations:** Number of steps blocked by policies
4. **P95 Latency:** 95th percentile latency in milliseconds
5. **Cost:** Total cost in USD

## Thresholds

Set thresholds for CI/CD gates:

- `--threshold-match`: Minimum accuracy (default: 0.0)
- `--threshold-viol`: Maximum policy violations (default: 0)
- `--threshold-hallu`: Maximum hallucination rate (default: 1.0)
- `--threshold-cost`: Maximum cost USD (default: inf)
- `--threshold-latency`: Maximum p95 latency ms (default: inf)

## Generating Reports

### JSON Report

```bash
python evals/report_generator.py \
  --db-url postgresql+psycopg://postgres:postgres@localhost:5432/ops_agents \
  --suite smoke \
  --output eval-report.json
```

### HTML Report

```bash
python evals/report_generator.py \
  --db-url postgresql+psycopg://postgres:postgres@localhost:5432/ops_agents \
  --suite smoke \
  --output eval-report.json \
  --html eval-report.html
```

### Before/After Comparison

```bash
# Generate comparison report
python evals/report_generator.py \
  --db-url postgresql+psycopg://postgres:postgres@localhost:5432/ops_agents_new \
  --before-db-url postgresql+psycopg://postgres:postgres@localhost:5432/ops_agents_old \
  --suite smoke \
  --output comparison-report.json \
  --html comparison-report.html
```

## CI/CD Integration

Use in GitHub Actions or other CI systems:

```yaml
- name: Run Evaluations
  run: |
    python evals/harness.py \
      --api http://localhost:8000 \
      --token ${{ secrets.EVAL_TOKEN }} \
      --suite smoke \
      --threshold-match 0.8 \
      --threshold-viol 0 \
      --threshold-hallu 0.1
```

The harness exits with code 1 if any thresholds are exceeded.

## Scorecards

Reports include scorecards with:
- Pass/fail status for each metric
- Threshold comparisons
- Pass rates
- Before/after improvements

## Best Practices

1. **Run Regularly:** Include in CI/CD pipeline
2. **Set Conservative Thresholds:** Start strict, relax gradually
3. **Track Trends:** Compare reports over time
4. **Monitor Costs:** Set cost thresholds to prevent runaway expenses
5. **Review Hallucinations:** Investigate high hallucination rates

## Adding New Test Cases

Create a new JSON file in `evals/cases/`:

```json
{
  "name": "my_test",
  "mode": "shadow",
  "description": "Test description",
  "expected": {
    "steps": [
      {"name": "step1", "tool": "github.create_issue"}
    ]
  }
}
```

Then run:
```bash
python evals/harness.py --suite my_test --api http://localhost:8000 --token $TOKEN
```

