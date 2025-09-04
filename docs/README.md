# TLDR Documentation

Welcome to the TLDR (AI Meeting Summarization Tool) documentation.

## 📁 Documentation Structure

### 🏗️ Architecture
- [`architecture/`](architecture/) - System design and architectural decisions
  - [`decisions/`](architecture/decisions/) - Architecture Decision Records (ADRs)
  - [`diagrams/`](architecture/diagrams/) - System architecture diagrams
  - [`README.md`](architecture/README.md) - Architecture overview

### 🔌 API Documentation
- [`api/`](api/) - API specifications and examples
  - [`examples/`](api/examples/) - Request/response examples
  - OpenAPI specifications

### 📚 Guides
- [`guides/`](guides/) - How-to guides and tutorials
  - [`developer/`](guides/developer/) - Developer setup and contribution guides
  - [`user/`](guides/user/) - End-user documentation

### 📋 Planning
- [`planning/`](planning/) - Project planning and implementation documents
  - [`implementation-plan.md`](planning/implementation-plan.md) - Complete implementation roadmap

### 🔧 Technical
- [`technical/`](technical/) - Technical specifications and deep dives
  - Data models and schemas
  - Integration specifications

## 🚀 Quick Start

1. **For Developers**: Start with [Developer Setup Guide](guides/developer/setup.md)
2. **For Users**: Check out the [User Guide](guides/user/getting-started.md)
3. **For Contributors**: Read our [Contributing Guidelines](../CONTRIBUTING.md)

## 🏛️ Architecture Overview

TLDR is built with a modern, modular architecture:

- **FastAPI Backend** - High-performance async API
- **Module-based Structure** - Organized by domain functionality
- **AI Services Integration** - OpenAI, AssemblyAI for transcription/summarization
- **Production-Ready** - Full CI/CD, testing, security from day one

## 📖 Key Documents

- [Implementation Plan](planning/implementation-plan.md) - Complete 10-phase development plan
- [Architecture Overview](architecture/README.md) - System design principles
- [API Specification](api/) - Complete API documentation
- [Contributing Guide](../CONTRIBUTING.md) - How to contribute to the project

## 🔄 Living Documentation

This documentation follows the "Living Documentation" principle - it evolves with the codebase and is maintained alongside code changes. All documentation is version-controlled and reviewed with the same rigor as code.

## 📝 Documentation Standards

We follow these standards for all documentation:

- **Audience-Focused**: Different docs for different audiences
- **Maintainable**: Docs are updated with code changes
- **Searchable**: Clear structure and navigation
- **Automated**: Generated from code where possible

---

**Need help?** Create an issue using our [templates](../.github/ISSUE_TEMPLATE/) or check our [Contributing Guide](../CONTRIBUTING.md).