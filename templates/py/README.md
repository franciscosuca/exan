# Python Semantic Release Template

This template contains the files necessary to set up Semantic Release for a Python project using Azure DevOps.

## How to use

1. **Copy Files**: Copy the contents of this folder (`.releaserc.json`, `package.json`, and the `pipe` folder) to the root of your Python project.

2. **Modify Parameters**:
    Open the copied files and replace the following placeholders with your project-specific values:

    * **`.releaserc.json`**:
        * Replace `{{PYTHON_PKG_DIR}}` with the path to your Python package directory (the directory containing `__init__.py` where the version is stored).
            * Example: If your structure is `src/my_app/__init__.py`, change it to `src/my_app`.
            * Ensure your `__init__.py` contains a `__version__ = "x.y.z"` line.

    * **Custom Version File (Alternative)**:
        If your project stores the version in a different file (e.g., `VERSION`, `pyproject.toml`, or `setup.py`), update `.releaserc.json` as follows:
        1. In the `semantic-release-replace-plugin` configuration, change the `files` array to point to your version file.
        2. Adjust the `from` regex pattern to match your versioning format.
        3. Update the `@semantic-release/git` plugin's `assets` array to include this file so the version bump is committed.

        *Example for a plain `VERSION` file:*

        ```json
        {
          "files": ["VERSION"],
          "from": "^.*$",
          "to": "${nextRelease.version}"
        }
        ```

    * **`pipe/azure-pipelines-semantic-release.yml`**:
        * This file is mostly generic. Review the triggers and paths to ensure they match your project structure.
        * The comments mention `{{PYTHON_PKG_DIR}}`, which is for your reference.

3. **Install Dependencies**:
    Run `npm install` to install the semantic-release dependencies.

4. **Configure Pipeline**:
    * Add the `pipe/azure-pipelines-semantic-release.yml` file to your Azure DevOps pipeline.
    * Ensure the `Semantic Release` job has the necessary permissions (Git write access) to push tags and update the changelog.
