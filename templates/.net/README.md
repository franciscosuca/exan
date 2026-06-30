# .NET Semantic Release Template

A ready-to-use template for .NET Core / C# projects configured with [`semantic-release`](https://github.com/semantic-release/semantic-release).

## Features

This template sets up automated version management and release automation with the following:

- **Conventional Commits with PR Support**: Uses the `conventionalcommits` preset with a custom parser pattern that correctly handles GitHub/Bitbucket "Merged PR" and merge commit message prefixes.
- **Semantic Versioning**: Configures release rules for major (breaking), minor (features), and patch (fixes/performance) releases.
- **Version File Management**:
  - Updates `VERSION.txt` with the new release version
  - Updates `.csproj` file version properties (`Version`, `AssemblyVersion`, `FileVersion`, `InformationalVersion`)
- **Standard Plugins**:
  - **`@semantic-release/commit-analyzer`**: Determines the next release version.
  - **`@semantic-release/release-notes-generator`**: Generates release notes with emoji-enhanced categories.
  - **`@semantic-release/changelog`**: Updates `CHANGELOG.md`.
  - **`@semantic-release/exec`**: Executes custom commands for version updates in `.csproj` files.
  - **`@semantic-release/git`**: Commits release assets back to the repository.

## Getting Started

1. **Copy Files**: Copy `.releaserc.json` and `package.json` to your project root.

2. **Update Placeholders**: Open `.releaserc.json` and replace:
   - `{{CSPROJ_PATH}}` with the path to your `.csproj` file (e.g., `MyProject/MyProject.csproj`)

3. **Keep Release Tooling in CI**: This template is set up so semantic-release packages are installed transiently in CI at runtime. You do not need to add them to your repository `package.json`.

4. **Configure Your `.csproj`**: Ensure your `.csproj` file has these version properties (if they don't exist, add them):

   ```xml
   <Version>0.0.0</Version>
   <AssemblyVersion>0.0.0</AssemblyVersion>
   <FileVersion>0.0.0</FileVersion>
   <InformationalVersion>0.0.0</InformationalVersion>
   ```

5. **Setup CI/CD Pipeline** (e.g., GitHub Actions):

    ```yaml
      - name: Release
         run: |
            npx \
               --package semantic-release@24.0.0 \
               --package @semantic-release/changelog@6.0.3 \
               --package @semantic-release/commit-analyzer@13.0.1 \
               --package @semantic-release/exec@6.0.3 \
               --package @semantic-release/git@10.0.1 \
               --package @semantic-release/release-notes-generator@14.1.0 \
               --package conventional-changelog-conventionalcommits@8.0.0 \
               semantic-release
         env:
            GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    ```

6. **Commit and Push**: Use conventional commit messages to trigger releases:
   - `feat:` → minor version bump
   - `fix:` → patch version bump  
   - `BREAKING CHANGE:` → major version bump

## Customization

### Modifying Version Rules

Edit the `releaseRules` in `.releaserc.json` to customize which commit types trigger releases.

### Updating Different Version Files

If your version is stored elsewhere (e.g., `VERSION` file or `appsettings.json`), modify the `@semantic-release/exec` `prepareCmd` in `.releaserc.json` accordingly.

### Pre-release Branches

The template includes a pre-release branch configuration. Modify the `branches` section in `.releaserc.json` if needed.
