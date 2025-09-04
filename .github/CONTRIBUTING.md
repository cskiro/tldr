# Contributing to TLDR

Thank you for your interest in contributing to TLDR! We welcome contributions from the community and appreciate your help in making this project better.

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please read it before contributing.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- UV package manager (recommended) or pip
- Git
- Docker (optional, for containerized development)

### Development Setup

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/yourusername/tldr.git
   cd tldr
   ```

3. **Create a virtual environment**:
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

4. **Install dependencies**:
   ```bash
   uv pip install -r requirements.txt
   uv pip install -r requirements-dev.txt
   ```

5. **Install pre-commit hooks**:
   ```bash
   pre-commit install
   ```

6. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

7. **Run tests to ensure everything works**:
   ```bash
   pytest
   ```

## Development Workflow

### 1. Create a Branch

Create a feature branch from `main`:

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b bugfix/your-bug-fix
```

### 2. Make Your Changes

- Write clean, readable code
- Follow the existing code style
- Add tests for new functionality
- Update documentation as needed

### 3. Test Your Changes

```bash
# Run the full test suite
pytest --cov=src --cov-report=term-missing

# Run linting
ruff check src/
black --check src/
mypy src/

# Run pre-commit checks
pre-commit run --all-files
```

### 4. Commit Your Changes

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```bash
git commit -m "feat: add new transcription service integration"
git commit -m "fix: resolve memory leak in summarization"
git commit -m "docs: update API documentation"
```

### 5. Push and Create a Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

## Code Style and Standards

### Python Code Style

- **Formatting**: Use Black with default settings
- **Linting**: Use Ruff for fast linting
- **Type Hints**: Use type hints for all functions and methods
- **Docstrings**: Use Google-style docstrings
- **Import Sorting**: Imports are sorted automatically by Ruff

### Code Quality Requirements

- **Test Coverage**: Minimum 80% coverage for new code
- **Type Checking**: All code must pass MyPy strict mode
- **No Console Logs**: Use proper logging instead of print/console.log
- **Error Handling**: Comprehensive error handling with proper exceptions

### Example Code Style

```python
from typing import List, Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

class MeetingSummary(BaseModel):
    """Meeting summary model with validation."""
    
    summary: str
    participants: List[str]
    action_items: Optional[List[str]] = None

async def process_transcript(transcript: str) -> MeetingSummary:
    """Process a meeting transcript and generate summary.
    
    Args:
        transcript: Raw meeting transcript text
        
    Returns:
        Processed meeting summary
        
    Raises:
        ProcessingError: If transcript processing fails
    """
    try:
        # Implementation here
        logger.info("Processing transcript of length %d", len(transcript))
        return MeetingSummary(summary="...", participants=[])
    except Exception as e:
        logger.error("Failed to process transcript: %s", e)
        raise ProcessingError("Transcript processing failed") from e
```

## Testing Guidelines

### Test Structure

```
tests/
├── unit/           # Unit tests
├── integration/    # Integration tests
├── e2e/           # End-to-end tests
├── fixtures/      # Test fixtures
└── conftest.py    # Pytest configuration
```

### Writing Tests

- **Test Naming**: Use descriptive names: `test_should_extract_action_items_when_transcript_contains_tasks`
- **Test Organization**: Group related tests in classes
- **Fixtures**: Use pytest fixtures for common setup
- **Mocking**: Mock external services and APIs
- **Async Tests**: Use `pytest-asyncio` for async code

### Example Test

```python
import pytest
from unittest.mock import AsyncMock
from src.summarization.service import SummarizationService

class TestSummarizationService:
    @pytest.fixture
    def service(self):
        return SummarizationService()
    
    @pytest.mark.asyncio
    async def test_should_extract_action_items_when_transcript_contains_tasks(
        self, service
    ):
        # Given
        transcript = "Alice will prepare the quarterly report by Friday"
        
        # When
        result = await service.summarize(transcript)
        
        # Then
        assert len(result.action_items) == 1
        assert "Alice" in result.action_items[0].assignee
        assert "quarterly report" in result.action_items[0].task
```

## Documentation

### README Updates

- Update the README.md if you add new features
- Include usage examples for new functionality
- Update installation instructions if needed

### API Documentation

- FastAPI generates automatic documentation
- Add comprehensive docstrings to all endpoints
- Include request/response examples

### Code Comments

- Comment complex business logic
- Explain "why" not "what"
- Keep comments up-to-date with code changes

## Pull Request Guidelines

### Before Submitting

- [ ] Code follows the style guidelines
- [ ] Tests pass with 80%+ coverage
- [ ] Documentation is updated
- [ ] Pre-commit hooks pass
- [ ] No merge conflicts with main branch

### PR Description Template

Use our [pull request template](.github/PULL_REQUEST_TEMPLATE.md) to ensure you provide all necessary information.

### Review Process

1. **Automated Checks**: CI pipeline must pass
2. **Code Review**: At least one maintainer review required
3. **Testing**: Manual testing for significant changes
4. **Documentation**: Verify documentation updates

## Issue Guidelines

### Bug Reports

Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md) and include:

- Clear description of the bug
- Steps to reproduce
- Expected vs actual behavior
- Environment details
- Screenshots if applicable

### Feature Requests

Use the [feature request template](.github/ISSUE_TEMPLATE/feature_request.md) and include:

- Clear description of the feature
- Use case and motivation
- Proposed implementation (if applicable)
- Alternative solutions considered

## Release Process

Releases are handled by maintainers:

1. Version bump in `pyproject.toml`
2. Update CHANGELOG.md
3. Create release tag
4. GitHub Actions handles deployment

## Community

### Getting Help

- **GitHub Discussions**: For questions and general discussion
- **GitHub Issues**: For bug reports and feature requests
- **Email**: For security issues (see SECURITY.md)

### Communication Guidelines

- Be respectful and constructive
- Provide clear, detailed information
- Help others when you can
- Follow the code of conduct

## Recognition

Contributors are recognized in:

- Release notes
- GitHub contributors page
- CONTRIBUTORS.md file (coming soon)

Thank you for contributing to TLDR! 🙏