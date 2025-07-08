# Contributing to GW2 WvW Leaderboards

Thank you for your interest in contributing to the GW2 WvW Leaderboards project! This document outlines our development standards and workflow.

## Git Workflow

We use a feature branch workflow with the following standards:

### Branch Naming Convention

Use the format: `<type>/<short-description>`

**Types:**
- `feat/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `test/` - Test additions or updates
- `refactor/` - Code refactoring
- `chore/` - Maintenance tasks

**Examples:**
- `feat/add-profession-rankings`
- `fix/date-filter-bug`
- `docs/update-api-reference`
- `test/add-integration-tests`
- `refactor/simplify-rating-system`
- `chore/update-dependencies`

### Commit Message Standards

We follow [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types:**
- `feat` - A new feature
- `fix` - A bug fix
- `docs` - Documentation only changes
- `style` - Changes that don't affect code meaning (white-space, formatting, etc)
- `refactor` - Code change that neither fixes a bug nor adds a feature
- `test` - Adding missing tests or correcting existing tests
- `chore` - Changes to build process or auxiliary tools

**Examples:**
```
feat(web-ui): add dark mode toggle

Add user-configurable dark mode with persistent settings stored in localStorage.
Includes updated CSS variables and toggle component in header.

Closes #123
```

```
fix(rating-system): resolve division by zero in Glicko calculations

Handle edge case where player has zero games played, preventing
crashes in rating calculation pipeline.

Fixes #456
```

```
docs: update API reference with new endpoints

- Add documentation for /api/v1/leaderboard endpoint
- Update schema examples with latest data structure
- Fix typos in installation guide
```

### Pull Request Process

1. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feat/your-feature-name
   ```

2. **Make your changes** following our coding standards

3. **Write tests** for new functionality

4. **Run the test suite** locally:
   ```bash
   python -m pytest tests/ -v
   ```

5. **Update documentation** if needed

6. **Commit your changes** using conventional commits:
   ```bash
   git commit -m "feat(core): add new rating calculation method"
   ```

7. **Push to your branch**:
   ```bash
   git push origin feat/your-feature-name
   ```

8. **Open a Pull Request** with:
   - Clear title following conventional commits format
   - Description of changes and motivation
   - Screenshots for UI changes
   - Reference to related issues

### PR Requirements

All PRs must:
- ✅ Pass all CI tests
- ✅ Include tests for new functionality
- ✅ Update documentation if needed
- ✅ Follow conventional commit format
- ✅ Be reviewed by at least one maintainer

## Development Setup

### Prerequisites
- Python 3.11+
- Git

### Installation
```bash
git clone https://github.com/pyrogw2/GW2LeaderBoard.git
cd GW2LeaderBoard
pip install -r requirements.txt  # If available
```

### Running Tests
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_web_ui_functionality.py -v

# Run with coverage
python -m pytest tests/ --cov=src/gw2_leaderboard
```

### Testing Web UI
```bash
# Generate test web UI
python workflow.py --ui-only

# Test with sample database
python workflow.py --latest-only --auto-confirm
```

## Code Standards

### Python Style
- Follow PEP 8 guidelines
- Use type hints where appropriate
- Maximum line length: 100 characters
- Use descriptive variable and function names

### Documentation
- Update `CLAUDE.md` for new commands or workflows
- Update `API_REFERENCE.md` for database schema changes
- Include docstrings for public functions
- Update `README.md` for user-facing changes

### Testing
- Write unit tests for new functions
- Include integration tests for complex workflows
- Test error conditions and edge cases
- Maintain test coverage above 80%

## Continuous Integration

Our CI pipeline automatically:
- Runs all tests on Python 3.11
- Tests web UI generation
- Validates database operations
- Checks import structure
- Verifies code quality

## Release Process

1. **Version Bump**: Update version in relevant files
2. **Changelog**: Update `CHANGELOG.md` with new features and fixes
3. **Tag Release**: Create annotated tag with version
4. **GitHub Release**: Create release with built executables

## Getting Help

- **Issues**: Use GitHub issues for bug reports and feature requests
- **Discussions**: Use GitHub discussions for questions and ideas
- **Discord**: Join our community Discord for real-time help

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Follow the Golden Rule

Thank you for contributing to the GW2 WvW Leaderboards! 🎉