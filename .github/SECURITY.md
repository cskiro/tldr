# Security Policy

## Supported Versions

We release patches for security vulnerabilities in the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

The TLDR team takes security seriously. We appreciate your efforts to responsibly disclose any vulnerabilities you may find.

### How to Report

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via one of the following methods:

1. **Email**: Send a detailed report to security@tldr-project.com
2. **Private Vulnerability Reporting**: Use GitHub's private vulnerability reporting feature (preferred)

### What to Include

When reporting a vulnerability, please include:

- A clear description of the vulnerability
- Steps to reproduce the issue
- Potential impact of the vulnerability
- Any suggested fixes (if available)
- Your contact information for follow-up questions

### Response Timeline

We aim to respond to security reports within:

- **24 hours**: Initial acknowledgment
- **72 hours**: Initial assessment and severity classification
- **7 days**: Detailed response with timeline for fixes
- **30 days**: Resolution (for critical vulnerabilities)

### Security Measures

Our application implements several security measures:

- **Input Validation**: All user inputs are validated and sanitized
- **Authentication**: JWT-based authentication with secure token handling
- **Authorization**: Role-based access control
- **Data Encryption**: Sensitive data encrypted at rest and in transit
- **API Rate Limiting**: Protection against abuse
- **Dependency Scanning**: Regular security scans of dependencies
- **Container Security**: Secure Docker configurations
- **HTTPS**: All communications over encrypted channels

### Privacy and Data Handling

- Meeting transcripts are processed securely and deleted after processing
- No audio data is permanently stored
- User data is handled in compliance with GDPR and privacy regulations
- API keys and secrets are never logged or exposed

### Scope

This security policy applies to:

- The main TLDR application
- All API endpoints
- Docker containers and deployment configurations
- Documentation and example code

### Out of Scope

The following are generally not considered security vulnerabilities:

- Issues in third-party dependencies (please report directly to the vendor)
- Social engineering attacks
- Physical attacks on hardware
- Denial of service attacks requiring extraordinary amounts of traffic

### Recognition

We believe in recognizing the contributions of security researchers. With your permission, we will:

- Credit you in our security advisories
- Include your name in our hall of fame
- Provide a reference letter for your security research work

Thank you for helping keep TLDR and our users safe!