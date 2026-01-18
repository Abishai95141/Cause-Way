#!/usr/bin/env python3
"""Document ingestion script for ChromaDB."""
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import chromadb
from chromadb.utils import embedding_functions

from app.config import CHROMA_PERSIST_DIR, EMBEDDING_MODEL, DATA_DIR


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start = end - overlap
    return chunks


def ingest_company_changes(collection, doc_path: Path):
    """Ingest company_changes.json."""
    print(f"Ingesting company changes from {doc_path}")
    
    with open(doc_path, "r") as f:
        changes = json.load(f)
    
    documents = []
    metadatas = []
    ids = []
    
    for change in changes:
        # Create a text representation
        text = f"""Change: {change.get('description', '')}
Type: {change.get('type', '')}
Date: {change.get('date', '')}
Affected Metrics: {', '.join(change.get('affected_metrics', []))}
Team: {change.get('team', '')}"""
        
        documents.append(text)
        metadatas.append({
            "type": "change",
            "change_id": change.get("id", ""),
            "change_type": change.get("type", ""),
            "date": change.get("date", "")
        })
        ids.append(f"change_{change.get('id', '')}")
    
    if documents:
        collection.add(documents=documents, metadatas=metadatas, ids=ids)
        print(f"  Added {len(documents)} change documents")
    
    return len(documents)


def ingest_experiments(collection, doc_path: Path):
    """Ingest past_experiments.md."""
    print(f"Ingesting experiments from {doc_path}")
    
    with open(doc_path, "r") as f:
        content = f.read()
    
    # Split by experiment sections
    sections = content.split("## EXP-")
    
    documents = []
    metadatas = []
    ids = []
    
    for i, section in enumerate(sections[1:], 1):  # Skip header
        # Get experiment ID from first line
        lines = section.strip().split("\n")
        exp_id = lines[0].split(":")[0].strip() if lines else f"exp_{i}"
        
        # Chunk larger sections
        chunks = chunk_text(section, chunk_size=800, overlap=100)
        
        for j, chunk in enumerate(chunks):
            documents.append(f"Experiment {exp_id}:\n{chunk}")
            metadatas.append({
                "type": "experiment",
                "experiment_id": f"EXP-{exp_id}",
                "chunk": j
            })
            ids.append(f"exp_{exp_id}_{j}")
    
    # Also add the best practices section
    if "Experiment Design Best Practices" in content:
        bp_start = content.find("## Experiment Design Best Practices")
        best_practices = content[bp_start:]
        chunks = chunk_text(best_practices, chunk_size=800, overlap=100)
        
        for j, chunk in enumerate(chunks):
            documents.append(chunk)
            metadatas.append({
                "type": "experiment",
                "experiment_id": "best_practices",
                "chunk": j
            })
            ids.append(f"exp_best_practices_{j}")
    
    if documents:
        collection.add(documents=documents, metadatas=metadatas, ids=ids)
        print(f"  Added {len(documents)} experiment documents")
    
    return len(documents)


def ingest_kpis(collection, doc_path: Path):
    """Ingest kpi_definitions.json."""
    print(f"Ingesting KPIs from {doc_path}")
    
    with open(doc_path, "r") as f:
        kpi_data = json.load(f)
    
    documents = []
    metadatas = []
    ids = []
    
    # Ingest metrics
    metrics = kpi_data.get("metrics", {})
    for metric_id, metric in metrics.items():
        text = f"""KPI: {metric.get('name', metric_id)}
Description: {metric.get('description', '')}
Formula: {metric.get('formula', '')}
Direction: {metric.get('direction', '')}
Owner Team: {metric.get('owner_team', '')}
Related Metrics: {', '.join(metric.get('related_metrics', []))}
Criticality: {metric.get('criticality', '')}"""
        
        documents.append(text)
        metadatas.append({
            "type": "kpi",
            "metric_id": metric_id,
            "owner_team": metric.get("owner_team", "")
        })
        ids.append(f"kpi_{metric_id}")
    
    # Ingest team info
    teams = kpi_data.get("teams", {})
    for team_id, team in teams.items():
        text = f"""Team: {team.get('name', team_id)}
Owned Metrics: {', '.join(team.get('owned_metrics', []))}
Stakeholder Metrics: {', '.join(team.get('stakeholder_metrics', []))}"""
        
        documents.append(text)
        metadatas.append({
            "type": "team",
            "team_id": team_id
        })
        ids.append(f"team_{team_id}")
    
    if documents:
        collection.add(documents=documents, metadatas=metadatas, ids=ids)
        print(f"  Added {len(documents)} KPI/team documents")
    
    return len(documents)


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("Document Ingestion for Causality-Aware Decision API")
    print("=" * 60)
    
    # Ensure directories exist
    Path(CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)
    
    # Initialize ChromaDB
    print(f"\nInitializing ChromaDB at {CHROMA_PERSIST_DIR}")
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    
    # Create embedding function
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )
    
    # Delete existing collection and recreate
    try:
        client.delete_collection("decision_documents")
        print("Deleted existing collection")
    except Exception:
        pass
    
    collection = client.create_collection(
        name="decision_documents",
        embedding_function=embedding_fn
    )
    print("Created fresh collection: decision_documents")
    
    # Ingest documents
    doc_dir = DATA_DIR / "documents"
    total_docs = 0
    
    # Company changes
    changes_path = doc_dir / "company_changes.json"
    if changes_path.exists():
        total_docs += ingest_company_changes(collection, changes_path)
    else:
        print(f"Warning: {changes_path} not found")
    
    # Past experiments
    experiments_path = doc_dir / "past_experiments.md"
    if experiments_path.exists():
        total_docs += ingest_experiments(collection, experiments_path)
    else:
        print(f"Warning: {experiments_path} not found")
    
    # KPI definitions
    kpis_path = doc_dir / "kpi_definitions.json"
    if kpis_path.exists():
        total_docs += ingest_kpis(collection, kpis_path)
    else:
        print(f"Warning: {kpis_path} not found")
    
    # Summary
    print("\n" + "=" * 60)
    print(f"Ingestion complete!")
    print(f"Total documents indexed: {total_docs}")
    print(f"Collection count: {collection.count()}")
    print("=" * 60)
    
    return total_docs


if __name__ == "__main__":
    doc_count = main()
    if doc_count < 10:
        print("\nWarning: Less than 10 documents indexed. Check data files.")
        sys.exit(1)
