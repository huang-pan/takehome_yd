#!/usr/bin/env python3
"""
YipitData Hybrid Semantic Search Pipeline.

This script executes the search pipeline which integrates sentence embeddings,
cosine similarity, and DuckDB storage to perform hybrid queries and filter AI/ML articles.

Steps Performed:
1. Loads enriched articles from a CSV file.
2. Generates sentence embeddings (default: 'all-MiniLM-L6-v2').
3. Computes the top 3 most similar articles for each row using cosine similarity.
4. Loads data and embeddings into an in-memory DuckDB database.
5. Performs a SQL hybrid search to filter AI/ML articles matching criteria.
6. Exports the filtered dataset to a CSV file.

Usage:
------
Run from the project root directory:
    $ PYTHONPATH=search python search/search.py

    Options:
      --input   Path to the input CSV (default: pipeline/data/output/ai_articles_enriched.csv)
      --output  Path to the output CSV (default: search/output/filtered_ai_articles_with_embeddings.csv)
      --model   SentenceTransformer model to use (default: all-MiniLM-L6-v2)

    Example with custom paths:
      $ PYTHONPATH=search python search/search.py \
            --input path/to/input.csv \
            --output path/to/output.csv \
            --model all-MiniLM-L6-v2

Run from within the 'search' directory:
    $ cd search
    $ python search.py --input ../pipeline/data/output/ai_articles_enriched.csv \
                       --output output/filtered_ai_articles_with_embeddings.csv
"""

import argparse
import json
import logging
from pathlib import Path
import numpy as np
import pandas as pd

from search_engine import SemanticSearchEngine

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("semantic_pipeline")

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="YipitData Hybrid Semantic Search Pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input",
        default="pipeline/data/output/ai_articles_enriched.csv",
        help="Path to enriched articles CSV input",
    )
    parser.add_argument(
        "--output",
        default="search/output/filtered_ai_articles_with_embeddings.csv",
        help="Path for the output CSV file with embeddings",
    )
    parser.add_argument(
        "--model",
        default="all-MiniLM-L6-v2",
        help="SentenceTransformer embedding model name",
    )
    return parser.parse_args()

def export_to_csv(df: pd.DataFrame, path: Path) -> None:
    """Write DataFrame to CSV, ensuring list fields are serialized as standard JSON."""
    df_export = df.copy()
    
    # Format embedding and top_similar_articles as clean JSON strings
    if "embedding" in df_export.columns:
        df_export["embedding"] = df_export["embedding"].apply(
            lambda x: json.dumps(x.tolist()) if hasattr(x, "tolist") else json.dumps(x)
        )
    if "top_similar_articles" in df_export.columns:
        df_export["top_similar_articles"] = df_export["top_similar_articles"].apply(
            lambda x: json.dumps(x.tolist()) if hasattr(x, "tolist") else (json.dumps(x) if isinstance(x, list) else x)
        )
        
    df_export.to_csv(path, index=False)
    logger.info("Successfully exported %d rows to '%s'", len(df_export), path)

def run_pipeline(input_path: Path, output_path: Path, model_name: str) -> None:
    logger.info("=== Starting Hybrid Semantic Search Pipeline ===")
    
    # 1. Read in enriched articles
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found at: '{input_path}'")
        
    logger.info("Loading enriched articles from '%s'...", input_path)
    df = pd.read_csv(input_path)
    logger.info("Loaded %d rows.", len(df))
    
    # Standardize index for consistent mapping with embeddings array
    df = df.reset_index(drop=True)
    
    # 2. Text Embedding Generation
    # Concatenate title + summary. Handle empty/null values gracefully.
    logger.info("Generating text embeddings using '%s' model...", model_name)
    df["text_to_embed"] = df["title"].fillna("") + ". " + df["summary"].fillna("")
    texts = df["text_to_embed"].tolist()
    
    engine = SemanticSearchEngine(model_name=model_name)
    embeddings = engine.generate_embeddings(texts)
    logger.info("Generated embeddings with shape %s.", embeddings.shape)
    
    # 3. Vector Similarity Search (Top 3 for each article) -> top_similar_articles column
    logger.info("Calculating top 3 most similar articles for each row...")
    similarity_matrix = np.dot(embeddings, embeddings.T)
    # Since embeddings are normalized by SentenceTransformer, dot product is cosine similarity
    
    norms = np.linalg.norm(embeddings, axis=1) # Lengths of all vectors
    # If not unit-normalized, division is required, but MiniLM embeddings are unit-normalized.
    # Just to be mathematically robust, we normalize similarity:
    norms_matrix = np.outer(norms, norms) # Matrix of ||u_i|| * ||u_j||
    similarity_matrix = similarity_matrix / np.maximum(norms_matrix, 1e-12)
    
    top_similar_list = []
    for idx in range(len(df)):
        sim_scores = similarity_matrix[idx]
        # Sort indices by similarity descending
        sorted_indices = np.argsort(sim_scores)[::-1]
        # Exclude self-similarity (the current index)
        filtered_indices = [i for i in sorted_indices if i != idx]
        # Pick top 3
        top_3_indices = filtered_indices[:3]
        top_3_ids = df.iloc[top_3_indices]["article_id"].tolist()
        top_similar_list.append(top_3_ids)
        
    df["top_similar_articles"] = top_similar_list
    
    # 4. DuckDB Load and Vector Storage
    logger.info("Loading data into DuckDB...")
    engine.load_data(df, embeddings)
    
    # 5. Part 3: Query & Export
    # All articles about "AI" or "Machine Learning" companies (filter by category and or industry)
    # Published between 2022-2024
    # With revenue >= $50M USD
    logger.info("Applying SQL filters & renaming columns using DuckDB...")
    
    query = """
    SELECT 
        article_id,
        title,
        company_name,
        published_date,
        category,
        revenue_usd,
        summary,
        url,
        meta_industry AS industry,
        meta_founded_year AS founded_year,
        meta_headquarters AS headquarters,
        meta_employee_count AS employee_count,
        meta_is_public AS is_public,
        meta_stock_ticker AS stock_ticker,
        company_age,
        company_size_category,
        embedding,
        top_similar_articles
    FROM articles
    WHERE 
        (category = 'AI_ML' OR meta_industry = 'AI/ML')
        AND pub_year BETWEEN 2022 AND 2024
        AND revenue_usd >= 50000000
    """
    
    filtered_df = engine.execute_sql(query)
    logger.info("Filtered dataset size: %d rows.", len(filtered_df))
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 6. Export
    export_to_csv(filtered_df, output_path)
    logger.info("=== Semantic Search Pipeline Complete ===")

if __name__ == "__main__":
    args = parse_args()
    run_pipeline(
        input_path=Path(args.input),
        output_path=Path(args.output),
        model_name=args.model,
    )
