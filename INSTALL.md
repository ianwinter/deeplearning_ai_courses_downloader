# Installation Guide

## Quick Install

```bash
# Install in development/editable mode (recommended for development)
pip install -e .

# Or install normally
pip install .
```

After installation, the `dl-ai` command will be available in your PATH.

## Verify Installation

```bash
# Check if dl-ai is installed
dl-ai --help

# Should show the help message with all available options
```

## Development Installation

If you're developing the package:

```bash
# Install in editable mode (changes to code are immediately available)
pip install -e .

# Install with development dependencies (if any)
pip install -e ".[dev]"
```

## Uninstall

```bash
pip uninstall dl-ai
```

## Troubleshooting

### Command not found

If `dl-ai` command is not found after installation:

1. Make sure the installation completed successfully
2. Check that your Python's `bin` directory is in your PATH
3. Try using `python -m main` instead (if installed in editable mode)

### Import errors

If you get import errors:

1. Make sure all dependencies are installed: `pip install -r requirements.txt` (if exists) or check `pyproject.toml`
2. Verify you're using the correct Python environment
3. Try reinstalling: `pip uninstall dl-ai && pip install -e .`



