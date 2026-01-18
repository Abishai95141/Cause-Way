#!/bin/bash
# Setup script for Causality-Aware Decision API

set -e

echo "=================================="
echo "Causality-Aware Decision API Setup"
echo "=================================="

# Check Python version
echo -e "\n[1/5] Checking Python version..."
python3 --version

# Create virtual environment
echo -e "\n[2/5] Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtual environment created."
else
    echo "Virtual environment already exists."
fi

# Activate and install dependencies
echo -e "\n[3/5] Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "Dependencies installed."

# Create directories
echo -e "\n[4/5] Creating directories..."
mkdir -p data/documents data/chroma_db database logs
echo "Directories created."

# Check Ollama
echo -e "\n[5/5] Checking Ollama..."
if command -v ollama &> /dev/null; then
    echo "Ollama is installed."
    if ollama list 2>/dev/null | grep -q "qwen2.5:7b"; then
        echo "✓ Model qwen2.5:7b is available."
    else
        echo "⚠️  Model qwen2.5:7b not found."
        echo "   Run: ollama pull qwen2.5:7b"
    fi
else
    echo "⚠️  Ollama not found."
    echo "   Install from: https://ollama.com/install"
fi

# Run document ingestion
echo -e "\n[6/6] Ingesting documents..."
if [ -f "data/documents/company_changes.json" ]; then
    python scripts/ingest_documents.py
else
    echo "⚠️  Data files not found. Skipping ingestion."
    echo "   Ensure data/documents/ contains the required JSON/MD files."
fi

echo -e "\n=================================="
echo "Setup complete!"
echo ""
echo "To start the server:"
echo "  source venv/bin/activate"
echo "  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "API will be available at: http://localhost:8000"
echo "API docs at: http://localhost:8000/docs"
echo "=================================="
