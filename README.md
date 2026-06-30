# Semantic Release Templates

This repository contains templates and configurations for implementing [Semantic Release](https://github.com/semantic-release/semantic-release) across various project types. The goal is to standardize versioning, changelog generation, and release publishing workflows.

> PENDING
>
> Update the project to tools-templates, and extend its content for pipeline-syncing and test coverage support

## Available Templates

### [![Node.js](https://img.shields.io/badge/Node.js-43853D?style=for-the-badge&logo=node.js&logoColor=white)](templates/js/)

Complete setup for Node.js / TypeScript applications with GitHub Actions CI/CD.

- **Status**: ✅ Available
- **Location**: `templates/js/`
- **Features**:
  - Automated version bumping based on conventional commits.
  - Automated tests with unit and end-to-end coverage.
  - GitHub Actions workflow for build, test, and semantic release.
  - Docker containerization support.
  - Semantic Release configuration with changelog generation.
  - Ready for GCP deployment (Cloud Run, App Engine, Cloud Functions).

### [![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](templates/py/)

Complete setup for Python projects with GitHub Actions CI/CD.

- **Status**: ✅ Available
- **Location**: `templates/py/`
- **Features**:
  - Automated version bumping based on conventional commits.
  - GitHub Actions workflow for build, test, and semantic release.
  - Python 3.11 support with pytest integration.
  - Docker containerization support.
  - Semantic Release configuration with changelog generation.
  - Ready for GCP deployment (Cloud Run, App Engine, Cloud Functions).

> NOTE
>
> Pending automated unit and end-to-end test coverage.

### ![.NET](https://img.shields.io/badge/.NET-512BD4?style=for-the-badge&logo=dotnet&logoColor=white)

Complete setup for .NET Core / C# applications.

- **Status**: ✅ Available
- **Location**: `templates/.net/`
- **Features**:
  - Automated version bumping based on conventional commits.
  - .csproj file version updates with semantic versioning.
  - VERSION.txt management for build pipelines.
  - GitHub Actions workflow ready.
  - Docker containerization support.
  - Semantic Release configuration with changelog generation.

  > NOTE
  >
  > Pending automated unit and end-to-end test coverage.

## Getting Started

Navigate to the specific template folder under `templates/` (e.g., `templates/js/` or `templates/py/`) and follow the `README.md` inside for:

- Integration instructions
- GitHub Actions workflow setup
- GCP deployment options
- Semantic Release configuration
