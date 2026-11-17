# Core Constitution & Engineering Guidelines

1. NO VIBE CODING: Never jump straight to writing code. Always verify if an approved specification exists in `.specify/tasks/` first.
2. DETERMINISTIC OUTPUTS: Use explicit typing (Type hints in Python / Pydantic / schemas), structured data models, and clean error handling.
3. QUALITY GATES: All code written must directly map to predefined requirements in the task spec, with unit tests covering core logic and edge cases.
4. TECH STACK:
   - Language & Runtime: Python 3.12, `boto3`
   - Infrastructure as Code: AWS SAM (`template.yaml`), CloudFormation specification
   - Cloud Services: AWS Lambda, Amazon API Gateway, Amazon DynamoDB, Amazon S3, AWS IAM
   - Local Emulation & Testing: Docker, AWS SAM CLI (`sam local`), `pytest`, `moto` (AWS mocking)
   - Security Baseline: AWS IAM Principle of Least Privilege (no wildcard `*` actions on sensitive resources, scoped resource ARNs).
