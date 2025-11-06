# Publishing to PyPI

This document explains how to publish `superset-sup` to PyPI.

## Package Information

- **Package Name**: `superset-sup`
- **Commands Installed**: `sup`, `preset-cli`, `superset-cli`
- **License**: Business Source License 1.1
- **Status**: Beta/Experimental

## Prerequisites

1. **PyPI Account**: You need a PyPI account with maintainer access to the `superset-sup` package
2. **API Token**: Generate a PyPI API token at https://pypi.org/manage/account/token/
3. **GitHub Secrets**: For automated publishing, ensure `PYPI_API_TOKEN` is set in repository secrets

## Publishing Methods

### Method 1: Automated Publishing via GitHub Actions (Recommended)

The repository includes a GitHub Actions workflow (`.github/workflows/python-publish.yml`) that automatically publishes to PyPI when a new release is created.

**Steps:**

1. Ensure all changes are committed and pushed to the `main` branch
2. Create a new git tag for the release:
   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```
3. Create a GitHub Release from the tag at https://github.com/preset-io/superset-sup/releases/new
4. The GitHub Action will automatically build and publish to PyPI

### Method 2: Manual Publishing

If you need to publish manually:

1. **Install build tools:**
   ```bash
   pip install build twine
   ```

2. **Clean previous builds:**
   ```bash
   rm -rf dist/ build/ src/*.egg-info
   ```

3. **Build the distribution packages:**
   ```bash
   python -m build
   ```

4. **Check the built packages:**
   ```bash
   ls -lh dist/
   # Should show both .tar.gz and .whl files
   ```

5. **Verify the package (optional but recommended):**
   ```bash
   twine check dist/*
   ```

6. **Upload to PyPI:**
   ```bash
   # For production PyPI
   twine upload dist/*

   # For TestPyPI (recommended for first-time testing)
   twine upload --repository testpypi dist/*
   ```

## Version Management

This project uses `setuptools_scm` for automatic version management based on git tags:

- Development builds: `0.0.post1.dev638+geaa24fa4d.d20251106` (auto-generated)
- Release builds: `0.1.0` (based on git tag)

To create a release version, simply create and push a git tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```

## Testing the Installation

After publishing, test the installation:

```bash
# Install from PyPI
pip install superset-sup

# Verify all three commands are available
sup --help
preset-cli --help
superset-cli --help
```

## Pre-Release Checklist

Before publishing a new version:

- [ ] Update CHANGELOG.rst with release notes
- [ ] Ensure all tests pass: `make test`
- [ ] Verify the build succeeds: `python -m build`
- [ ] Review README.md for accuracy
- [ ] Ensure LICENSE.txt is up to date
- [ ] Test installation in a clean virtual environment
- [ ] Tag the release in git: `git tag v0.X.Y`

## Publishing to TestPyPI First

For beta releases, it's recommended to publish to TestPyPI first:

1. **Upload to TestPyPI:**
   ```bash
   twine upload --repository testpypi dist/*
   ```

2. **Test installation from TestPyPI:**
   ```bash
   pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ superset-sup
   ```

3. **If everything works, publish to production PyPI:**
   ```bash
   twine upload dist/*
   ```

## Troubleshooting

### Build Warnings

You may see deprecation warnings about license configuration. These are informational and don't prevent publishing:
- `project.license as a TOML table is deprecated`
- These will be addressed in future setuptools updates

### Version Conflicts

If you get "File already exists" errors from PyPI:
- You cannot re-upload the same version number
- Create a new git tag with an incremented version
- Clean and rebuild: `rm -rf dist/ && python -m build`

## Support

For issues or questions:
- GitHub Issues: https://github.com/preset-io/superset-sup/issues
- Legacy CLI Docs: https://github.com/preset-io/preset-cli
