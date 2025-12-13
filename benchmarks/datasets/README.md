# Benchmark Datasets (schemas)

Schemas for local slices (content to be populated later):

## gpqa_lite_v1.jsonl
Each line:
```json
{
  "question_id": "gpqa_0001",
  "question": "TEXT_OF_QUESTION",
  "options": {
    "A": "option A text",
    "B": "option B text",
    "C": "option C text",
    "D": "option D text"
  },
  "correct_option": "B",
  "category": "physics"
}
```

## swe_lite_v1.jsonl
Each line:
```json
{
  "issue_id": "swe_lite_0012",
  "repo": "owner/project",
  "issue_title": "Short title",
  "issue_body": "Original GitHub issue description.",
  "test_command": "pytest path/to/tests -k 'specific_case'",
  "notes": "Any constraints or hints you want to preserve."
}
```
