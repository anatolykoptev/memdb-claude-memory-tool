#!/usr/bin/env bash
# scripts/publish.sh — Build sdist + wheel, validate, publish to PyPI.
#
# Prereqs:
#   - PYPI_TOKEN in env OR ~/.pypirc configured (use API token, not password)
#   - python -m pip install --upgrade build twine
#   - Clean working tree (uncommitted changes will fail)
#
# Usage:
#   bash scripts/publish.sh              # publish to PyPI
#   bash scripts/publish.sh --testpypi   # publish to TestPyPI first (recommended)
#   bash scripts/publish.sh --dry-run    # build only, no upload

set -euo pipefail
trap 'echo "ERROR on line $LINENO" >&2' ERR

DRY_RUN=0
TEST=0
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        --testpypi) TEST=1 ;;
        *) echo "unknown arg: $arg"; exit 1 ;;
    esac
done

# 1. Clean state check
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "ERROR: uncommitted changes — commit or stash first"
    exit 2
fi

# 2. Verify version in pyproject.toml matches latest git tag
VERSION=$(python3 -c "import tomllib; f=open('pyproject.toml','rb'); print(tomllib.load(f)['project']['version'])")
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
LAST_TAG_VERSION="${LAST_TAG#v}"
echo "pyproject version: $VERSION, last git tag: $LAST_TAG"
if [[ "$VERSION" != "$LAST_TAG_VERSION" ]]; then
    echo "WARN: pyproject version ($VERSION) does not match last tag ($LAST_TAG)"
    echo "      Did you git tag v$VERSION yet?"
fi

# 3. Clean dist/
rm -rf dist/ build/ src/*.egg-info

# 4. Build
echo "==> Building sdist + wheel"
python3 -m build

# 5. Validate
echo "==> Validating with twine check"
python3 -m twine check dist/*

# 6. Show what will be uploaded
echo "==> Files to upload:"
ls -la dist/

if [[ $DRY_RUN -eq 1 ]]; then
    echo "==> DRY RUN — skipping upload"
    exit 0
fi

# 7. Upload
if [[ $TEST -eq 1 ]]; then
    echo "==> Uploading to TestPyPI"
    python3 -m twine upload --repository testpypi dist/*
    echo "Test install: pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ memdb-claude-memory==$VERSION"
else
    echo "==> Uploading to PyPI"
    python3 -m twine upload dist/*
    echo "Install: pip install memdb-claude-memory==$VERSION"
fi

echo "==> Done"
