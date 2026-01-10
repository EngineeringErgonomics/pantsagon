# Variables

Variables are declared in `pack.yaml` and mirrored in `copier.yml`.

Policy:

- every manifest variable must exist in copier questions
- undeclared copier variables are errors (default)
- default mismatches are warnings (strict mode turns warnings into errors)
