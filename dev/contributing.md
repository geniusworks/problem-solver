# Contributing Guidelines

Thank you for your interest in contributing to the Problem Solver project! This document provides guidelines and best practices for contributing.

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
