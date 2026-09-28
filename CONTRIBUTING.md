## Contributing guidelines

- **Issues & feature requests**
  - Use the issue tracker to report bugs, request features, or propose enhancements.
  - When reporting a bug, include:
    - Clear steps to reproduce.
    - What you expected to happen.
    - What actually happened, including logs and stack traces when possible.

- **Pull requests**
  - Fork the repository and create feature branches from the main branch.
  - Keep changes focused and small where possible.
  - Add or update tests for all behavioral changes.
  - Ensure `pytest` passes and that you have not introduced linter or type errors.
  - Describe the motivation, design decisions, and any breaking changes in the PR description.

- **Coding style**
  - Follow **PEP 8** for Python code style.
  - Prefer small, composable functions and clear docstrings over comments that can get out of date.
  - Keep configuration‑specific logic behind well‑named helpers or settings services.

- **Security**
  - Never commit real credentials, API keys, or private data.
  - If you suspect a security issue, please report it through the project's support contact rather than opening a public issue.

