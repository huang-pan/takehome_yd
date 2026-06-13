import pandas as pd
import duckdb
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from typing import List, Tuple, Any, Optional

class SemanticSearchEngine:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", db_path: str = ":memory:"):
        """
        Initialize the SemanticSearchEngine.
        
        Args:
            model_name: The sentence-transformer model name.
            db_path: Path to the DuckDB file, or ':memory:' for in-memory database.
        """
        self.model = SentenceTransformer(model_name)
        self.conn = duckdb.connect(db_path)
        self.is_loaded = False
        
    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Generate text embeddings using sentence-transformers.
        
        Args:
            texts: List of input strings.
            
        Returns:
            A numpy array of shape (len(texts), embedding_dim).
        """
        return self.model.encode(texts, show_progress_bar=False)
        
    def load_data(self, df: pd.DataFrame, embeddings: np.ndarray) -> None:
        """
        Load clean data and pre-computed embeddings into DuckDB.
        
        Args:
            df: Pandas DataFrame containing the articles data.
            embeddings: Numpy array containing embeddings for the articles.
        """
        df_copy = df.copy()
        
        # Convert embeddings numpy array to a list of floats for DuckDB list support
        df_copy["embedding"] = [emb.tolist() for emb in embeddings]
        
        # Register DataFrame in DuckDB and write to table
        self.conn.register("temp_df", df_copy)
        self.conn.execute("DROP TABLE IF EXISTS articles")
        self.conn.execute("CREATE TABLE articles AS SELECT * FROM temp_df")
        self.conn.unregister("temp_df")
        self.is_loaded = True
        
    def execute_sql(self, query_str: str) -> pd.DataFrame:
        """
        Execute SQL query on DuckDB and return a DataFrame.
        
        Args:
            query_str: Standard SQL query string.
            
        Returns:
            Pandas DataFrame of results.
        """
        return self.conn.execute(query_str).df()
        
    def _resolve_query_embedding(self, query: str) -> np.ndarray:
        """
        Resolves query into an embedding. If query matches a stored article_id,
        it retrieves the precomputed embedding. Otherwise, encodes the query string.
        """
        if not self.is_loaded:
            raise ValueError("Data not loaded. Call load_data() first.")
            
        # Try to look up query as article_id
        res = self.conn.execute(
            "SELECT embedding FROM articles WHERE article_id = ?", (query,)
        ).fetchone()
        
        if res is not None:
            return np.array(res[0])
            
        # If not found, encode as new search query
        return self.generate_embeddings([query])[0]
        
    def find_similar_articles(self, query_text: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        Perform cosine similarity search against all articles.
        
        Args:
            query_text: Natural language query string or an article_id.
            top_k: Number of top similar articles to return.
            
        Returns:
            A list of tuples (article_id, score).
        """
        if not self.is_loaded:
            raise ValueError("Data not loaded. Call load_data() first.")
            
        query_emb = self._resolve_query_embedding(query_text)
        
        # Fetch all article IDs and embeddings
        res = self.conn.execute("SELECT article_id, embedding FROM articles").fetchall()
        if not res:
            return []
            
        article_ids = [r[0] for r in res]
        all_embeddings = np.array([r[1] for r in res])
        
        # Compute cosine similarities
        scores = cosine_similarity([query_emb], all_embeddings)[0]
        
        # Pair and sort
        id_score_pairs = list(zip(article_ids, scores))
        id_score_pairs.sort(key=lambda x: x[1], reverse=True)
        
        return id_score_pairs[:top_k]
        
    def hybrid_search(self, query_text: str, sql_filters: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        Perform hybrid search: apply SQL filters first, then compute vector similarity on the subset.
        
        Args:
            query_text: Natural language query string or an article_id.
            sql_filters: SQL WHERE clause string (e.g. "pub_year >= 2022 AND revenue_usd > 50000000").
            top_k: Number of top similar articles to return.
            
        Returns:
            A list of tuples (article_id, score).
        """
        if not self.is_loaded:
            raise ValueError("Data not loaded. Call load_data() first.")
            
        # Fetch filtered subset
        query = f"SELECT article_id, embedding FROM articles WHERE {sql_filters}"
        res = self.conn.execute(query).fetchall()
        if not res:
            return []
            
        article_ids = [r[0] for r in res]
        all_embeddings = np.array([r[1] for r in res])
        
        query_emb = self._resolve_query_embedding(query_text)
        
        # Compute cosine similarities
        scores = cosine_similarity([query_emb], all_embeddings)[0]
        
        # Pair and sort
        id_score_pairs = list(zip(article_ids, scores))
        id_score_pairs.sort(key=lambda x: x[1], reverse=True)
        
        return id_score_pairs[:top_k]
