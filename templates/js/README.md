# JS Semantic Release Template

A ready-to-use template for JavaScript/Node.js projects configured with [`semantic-release`](https://github.com/semantic-release/semantic-release) and prepared for Azure DevOps pipeline integration.

## Features

This template sets up automated version management and package publishing with the following enhancements:

- **Conventional Commits with PR Support**: Uses the `conventionalcommits` preset with a custom parser pattern that correctly handles GitHub/Bitbucket "Merged PR" and merge commit message prefixes.
- **Detailed Release Rules**: Configured to trigger patch releases for `perf`, `refactor`, and `style` changes in addition to standard `fix` and `feat` (minor) releases.
- **Standard Plugins**:
  - **`@semantic-release/commit-analyzer`**: Determines the next release version.
  - **`@semantic-release/release-notes-generator`**: Generates release notes.
  - **`@semantic-release/changelog`**: Updates `CHANGELOG.md`.
  - **`@semantic-release/npm`**: Updates version in `package.json` (configured with `npmPublish: false` by default).
  - **`@semantic-release/git`**: Commits release assets back to the repository.
  - **`@semantic-release/github`**: Creates GitHub releases.

## Getting Started

1. Copy `.releaserc.json` and `package.json` details into your project.
2. Setup CI/CD pipeline to run semantic-release on your release branches.
3. Ensure your `GITHUB_TOKEN` (and `NPM_TOKEN` if you decide to publish to an npm registry) are configured in your CI environment.

The template pipelines install and run semantic-release packages at runtime with pinned versions, so you do not need to add semantic-release devDependencies to your project.

## Azure DevOps Pipeline Convention

Use the following standard location in this template:

- Pipeline folder: `pipe/`
- Pipeline file: `pipe/azure-pipelines-semantic-release.yml`

The pipeline file is a generic Azure DevOps template intended to be reusable across JavaScript projects and runs semantic-release packages directly from the pipeline.
