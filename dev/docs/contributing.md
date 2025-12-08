# Contributing Guidelines

Thank you for your interest in contributing to the Problem Solver project! This document provides guidelines and best practices for contributing.

## Core Principles

These principles guide all development and improvement work on the Problem Solver:

### 1. Solver Autonomy

The solver must remain fully autonomous. All solutions must be generated through the LLM orchestration pipeline—never by hand-authoring canonical solution files outside that process.

- **No manual solutions**: Do not create or commit hand-written solution files to compensate for LLM failures.
- **No "super AI interventions"**: Fixes must not rely on external intelligence (human or otherwise) injecting solutions outside the pipeline.
- **Fix upstream, not downstream**: When the solver fails, address the root cause by improving parsing, prompting, evaluation, consensus, or orchestration—not by bypassing the pipeline.

### 2. General-Purpose Improvements

All improvements must have general utility and advance the goal of autonomous, one-shot, locally orchestrated LLM intelligence. Avoid overfit one-offs.

- **No problem-specific hacks**: Do not add code or prompts that are tailored to a single problem instance with no broader applicability.
- **Pattern-class guidance is acceptable**: Problem-specific clarifications in prompts are fine when they apply to a recognizable *class* of problems (e.g., corrupted-memory parsing puzzles) and are triggered by heuristics on problem text—not hard-coded for a particular day.
- **Preserve existing behavior**: Improvements must not regress earlier successes. Test broadly before merging.

### 3. Prompt Guidance Discipline

Prompt guidance must empower LLM problem-solving intuition without constraining it or giving away solutions. The ideal prompt guidance:

- **Classifies** problems into recognizable algorithmic patterns (e.g., "linear string scanning", "graph traversal", "dynamic programming")
- **Provides wisdom** about that pattern class—common pitfalls, efficient approaches, things to watch for
- **Does NOT** restate the problem description or provide the solution algorithm
- **Does NOT** include problem-specific values, character counts, or magic numbers
- **Is more general** than any particular problem, yet concrete enough to narrow and amplify effort

**The test**: If the guidance would essentially "give away" the solution to a specific problem, it's overfit. The LLM should derive the algorithm from the problem description itself. Guidance should bound and empower, not dictate.

**Anti-patterns to avoid**:
- Restating problem steps as "guidance"
- Including exact string lengths, specific patterns, or solution pseudocode
- Triggering on verbatim problem phrases (e.g., "total distance between your lists")
- Adding guidance that only applies to one problem instance

## Code Style

- Follow PEP 8 style guidelines for Python code
- Use meaningful variable and function names
- Include docstrings for all functions and classes
- Add type hints to function parameters and return values
- Keep functions focused and single-purpose
- Maximum line length: 100 characters

## Development Process

1. **Fork and Clone**
   - Fork the repository on GitHub
   - Clone your fork locally
   - Add the upstream repository as a remote

2. **Branch**
   - Create a new branch for each feature or fix
   - Use descriptive branch names (e.g., `feature/add-new-model`, `fix/rate-limit-handling`)

3. **Development**
   - Write tests for new features
   - Ensure all tests pass locally
   - Update documentation as needed
   - Keep commits atomic and well-described

4. **Pull Request**
   - Push your changes to your fork
   - Create a Pull Request against the main repository
   - Fill out the PR template completely
   - Respond to review comments

## Testing

- Write unit tests for new functionality
- Ensure existing tests pass
- Add integration tests for new features
- Include test cases for error conditions

## Documentation

Update documentation when you:
- Add new features
- Modify existing functionality
- Change configuration options
- Add new dependencies

## Commit Messages

Follow conventional commits format:
```
type(scope): description

[optional body]
[optional footer]
```

Types:
- feat: New feature
- fix: Bug fix
- docs: Documentation changes
- style: Code style changes
- refactor: Code refactoring
- test: Adding tests
- chore: Maintenance tasks

## Questions?

If you have questions about contributing:
1. Check existing issues and documentation
2. Open a new issue with the "question" label
3. Be specific about what you're trying to accomplish
