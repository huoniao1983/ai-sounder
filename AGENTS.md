# Repository Guidelines

AISounder is an AI live-streaming assistant under active implementation. This guide is the shared contributor contract for agents and humans.

## Project Structure & Module Organization

- `engine/` - Python engine: platform adapters, TTS, scheduler, audio, leads, NLP, content and IPC.
- `desktop/` - Tauri 2 + React/TypeScript shell.
- `tests/` - pytest suite mirroring `engine/` behavior.
- `docs/` - PRD and development plan.
- `assets/music/` - licensed built-in BGM assets.

Keep generated or third-party assets out of source directories, and commit no API keys or credentials.

## Build, Test, and Development Commands

Run the Python engine tests and sidecar from the repository root:

```powershell
python -m pytest
'{"id":1,"method":"health","params":{}}' | python -m engine.main --db-url "sqlite:///:memory:"
python -m engine.api_server --host 127.0.0.1 --port 8765
```

Run the desktop shell from `desktop/`:

```powershell
npm install
npm run dev
npm run tauri dev
npm run build
```

## Coding Style & Naming Conventions

- Use LF line endings, UTF-8, and two-space indentation unless the chosen language standard says otherwise.
- Use English identifiers, commit messages, and code comments; product-facing docs and UI copy may use Chinese.
- Name files in lowercase with hyphens, classes in `PascalCase`, functions and variables in `camelCase`, and constants in `UPPER_SNAKE_CASE`.
- Use the formatting and linting tools included in the project stack, keeping their configs at the repository root.

## Testing Guidelines

Write pytest cases in `tests/`, runnable with `python -m pytest`. Name test files and functions after the behavior they verify and assert observable behavior rather than private internals. Python code may require NumPy or SQLAlchemy; audio extras such as sounddevice and miniaudio stay optional.

## Commit & Pull Request Guidelines

- Use Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, and `chore:`.
- Keep commits small and avoid mixing unrelated changes.
- Pull requests need a descriptive title and summary, links to related issues, verification notes, and screenshots or recordings for UI changes.

## Security & Configuration Tips

Never commit secrets, API keys, tokens, or live-streaming credentials. The UI may keep a local model-provider API key for development; production persistence should move to encrypted local storage or environment variables.
