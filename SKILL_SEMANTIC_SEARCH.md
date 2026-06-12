# Technical Assessment — YipitData Semantic Search

**Role:** Data Engineer

## Context

Implement semantic search using embeddings, a vector database, and vector similarity.

## The dataset

`pipeline/data/output/ai_articles_enriched.csv` - contains AI-relevant articles enriched with company metadata

## Your task

Part 2: Integration with Vector Database

Implement semantic search using embeddings:

Requirements
1. Text Embedding Generation
- read in `pipeline/data/output/ai_articles_enriched.csv`
- Generate embeddings for article titles + summaries (concatenated)
- Use `sentence-transformers` library with `all-MiniLM-L6-v2` model or equivalent
- Store embeddings as numpy arrays

2. Vector Similarity Search
- Implement cosine similarity search
- Function: `find_similar_articles(query_text, top_k=5)`
- Return article IDs and similarity scores

3. DuckDB Integration with Vector Storage
- Load cleaned data into DuckDB
- Store embeddings using DuckDB's ARRAY type or as JSON
- Create a function for hybrid search: SQL filters + vector similarity
- Example: "Find AI-related articles from 2022-2024 with revenue > $50M, similar to article X"

Part 3: Query Interface & Export

Required Deliverable:

Create a pipeline that exports a CSV file containing:
- All articles about "AI" or "Machine Learning" companies (filter by category and or industry)
- Published between 2022-2024
- With revenue >= $50M USD
- Include columns: `article_id`, `title`, `company_name`, `published_date`, `category`, `revenue_usd`, `summary`, `url`, `industry`, `founded_year`, `headquarters`, `employee_count`, `is_public`, `stock_ticker`, `company_age`, `company_size_category` , `embedding` (as array/list), top_similar_articles,
- Add a `top_similar_articles` column containing IDs of top 3 most similar articles

Query Functions:
1. Function to execute SQL queries on DuckDB
2. Function to perform vector similarity search
3. Export function to Csv with embeddings

## Deliverables

1. Code Implementation
- Put all code and associated markdown files into the semantic_search subdirectory
- Clean, modular Python code organized in functions/classes
- A main pipeline script that processes the data and generates the output
- Proper error handling for edge cases

2. Documentation (Keep it concise!)

README.md (Max 1 page):
- Installation instructions (dependencies)
- How to run the pipeline (step-by-step)
- Example usage of key functions
- System requirements

EXPLAIN.md (Max 1.5 pages):
- Your approach and key decisions
- Choice of embedding model and why
- How you handled edge cases in data cleaning
- Trade-offs you made (performance vs. accuracy)
- What you would improve with more time

requirements.txt:
- All dependencies with versions

## Constraints

- **Python 3.10+.**
- **Recommended Libraries:** standard library preferred. pandas duckdb numpy scikit-learn sentence-transformers pyarrow

## Evaluation criteria

Technical Excellence (45%)
- Code quality and organization
- Correct implementation of vector search
- Efficient data processing

AI/ML Integration (25%)
- Proper use of embedding models
- Quality of semantic search results
- Effective vector similarity implementation

Data Engineering Best Practices (20%)
- Data validation and quality checks
- Proper use of DuckDB features
- Clean data transformations

Documentation (10%)
- Clear README with working instructions
- Well-explained decisions in EXPLAIN.md

## Notes & clarifications

1. Loading Sentence Transformers:
from sentence_transformers import SentenceTransformer model = SentenceTransformer('all-MiniLM-L6-v2') embeddings = model.encode(texts) # texts is a list of strings

2. Cosine Similarity:
from sklearn.metrics.pairwise import cosine_similarity similarity_scores = cosine_similarity([query_embedding], all_embeddings)[0]

3. DuckDB with Arrays:
import duckdb conn = duckdb.connect(':memory:') # Store embeddings as JSON or use ARRAY type df['embedding_json'] = df['embedding'].apply(lambda x: x.tolist()) conn.execute("CREATE TABLE articles AS SELECT * FROM df")
