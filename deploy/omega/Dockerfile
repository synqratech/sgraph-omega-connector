FROM python:3.12-slim

WORKDIR /workspace/omega-src

# Keep omega runtime dependencies inside image to avoid reinstall on each restart.
RUN pip install --no-cache-dir \
    "numpy>=1.24" \
    "PyYAML>=6.0" \
    "jsonschema>=4.0" \
    "fastapi>=0.110" \
    "uvicorn>=0.29" \
    "python-multipart>=0.0.9" \
    "cryptography>=42.0" \
    "pypdf>=4.0" \
    "python-docx>=1.1" \
    "beautifulsoup4>=4.12" \
    "lxml>=5.0"
