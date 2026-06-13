import pytest
import pandas as pd
import numpy as np
import json
from search.search_engine import SemanticSearchEngine

@pytest.fixture
def sample_df():
    data = {
        "article_id": ["ART0001", "ART0002", "ART0003"],
        "title": [
            "Scale AI Raises Series D Funding",
            "DataRobot Announces Breakthrough LLM",
            "NVIDIA Achieves Profitability Milestone",
        ],
        "company_name": ["Scale AI", "DataRobot", "NVIDIA"],
        "published_date": ["2020-02-21", "2023-02-23", "2022-10-26"],
        "pub_year": [2020, 2023, 2022],
        "category": ["FinTech", "SaaS_Software", "AI_ML"],
        "revenue_usd": [0, 312151151, 6649800000],
        "summary": [
            "Model performance and efficiency advances.",
            "Strategic acquisition strengthens LLM capabilities.",
            "Financial results exceed analyst expectations.",
        ],
        "url": [
            "https://technews.example.com/1",
            "https://technews.example.com/2",
            "https://technews.example.com/3",
        ],
        "meta_industry": ["AI/ML", "Cloud Computing", "AI/ML"],
        "meta_founded_year": [2016, 2012, 1993],
        "meta_headquarters": ["Berlin, Germany", "New York, NY", "London, UK"],
        "meta_employee_count": [23379, 23471, 22031],
        "meta_is_public": [False, True, True],
        "meta_stock_ticker": [None, None, "NVDA"],
        "company_age": [4, 11, 29],
        "company_size_category": ["Medium", "Medium", "Medium"],
    }
    return pd.DataFrame(data)

def test_generate_embeddings():
    engine = SemanticSearchEngine()
    texts = ["Scale AI raises Series D", "NVIDIA profitability results"]
    embs = engine.generate_embeddings(texts)
    
    assert isinstance(embs, np.ndarray)
    assert embs.shape == (2, 384)  # all-MiniLM-L6-v2 uses 384 dimensions
    
def test_load_data_and_sql(sample_df):
    engine = SemanticSearchEngine()
    texts = (sample_df["title"] + ". " + sample_df["summary"]).tolist()
    embs = engine.generate_embeddings(texts)
    
    engine.load_data(sample_df, embs)
    assert engine.is_loaded
    
    # Execute SQL
    res_df = engine.execute_sql("SELECT count(*) as count FROM articles")
    assert res_df.loc[0, "count"] == 3
    
def test_find_similar_articles(sample_df):
    engine = SemanticSearchEngine()
    texts = (sample_df["title"] + ". " + sample_df["summary"]).tolist()
    embs = engine.generate_embeddings(texts)
    engine.load_data(sample_df, embs)
    
    # Find similar to Scale AI (ART0001)
    results = engine.find_similar_articles("ART0001", top_k=2)
    assert len(results) == 2
    assert results[0][0] == "ART0001"  # Self should be most similar
    
    # Query text search
    results_text = engine.find_similar_articles("NVIDIA financial results", top_k=1)
    assert len(results_text) == 1
    assert results_text[0][0] == "ART0003"
    
def test_hybrid_search(sample_df):
    engine = SemanticSearchEngine()
    texts = (sample_df["title"] + ". " + sample_df["summary"]).tolist()
    embs = engine.generate_embeddings(texts)
    engine.load_data(sample_df, embs)
    
    # Hybrid search: Category AI_ML, similar to ART0002
    results = engine.hybrid_search("ART0002", "category = 'AI_ML'", top_k=1)
    assert len(results) == 1
    assert results[0][0] == "ART0003"  # Only ART0003 matches category AI_ML
