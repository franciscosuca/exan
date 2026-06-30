
# Git Submodules

> Recommended approach for consuming this repository with explicit version pinning.

## Use `semantic-release-template` as a Git submodule

This document intentionally covers the submodule workflow only.

Repository used in the examples:

```text
https://github.com/franciscosuca/semantic-release-template.git
```

### Option A: Add the full template repository as a submodule

```bash
# From the root of your target repository
git submodule add https://github.com/franciscosuca/semantic-release-template.git .semantic-release-template
git commit -m "chore: add semantic-release-template submodule"
```

This pins a specific commit of `semantic-release-template` in `.semantic-release-template/`.

### Option B: Place the submodule in a specific folder path

You can place the submodule in any folder of your project (not only the root).

```bash
# Example: keep release assets under tooling/
git submodule add https://github.com/franciscosuca/semantic-release-template.git tooling/semantic-release-template
git commit -m "chore: add semantic-release-template submodule under tooling"
```

Use this when you want the submodule isolated inside a specific area of your repository.

### Use only one template folder from the submodule

Even when the submodule points to the whole repository, you can consume only the folder you need, for example:

- `tooling/semantic-release-template/templates/js/`
- `tooling/semantic-release-template/templates/py/`

### Pull upstream changes

When you want to move to a newer pinned version:

```bash
# Replace <submodule-path> with your chosen location
git submodule update --remote <submodule-path>
git add <submodule-path>
git commit -m "chore: update semantic-release-template submodule"
```

Examples of `<submodule-path>`:

- `.semantic-release-template`
- `tooling/semantic-release-template`

### Clone a repository that already contains this submodule

```bash
git clone --recurse-submodules https://github.com/yourorg/yourrepo
# or, after a plain clone:
git submodule update --init --recursive
```