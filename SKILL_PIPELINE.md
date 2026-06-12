# Technical Assessment — YipitData Core ETL Pipeline

**Role:** Data Engineer

## Context

Build a clean, repeatable ETL pipeline that processes technology news articles.

## The dataset

`pipeline/data/input/tech_news.csv` - Contains news articles about technology companies (500 rows)

`pipeline/data/input/company_metadata.json` - Contains additional company information

The data is intentionally messy and requires cleaning and transformation.

## Your task

Build a Python pipeline that, given `tech_news.csv`, produces a clean, readable HTML rendering of each opinion. Specifically:

Part 1: Core ETL Pipeline
pip
Create essential data cleaning functions:
1. Revenue Cleaning - Clean the "revenue" column:
- Convert all amounts to USD (handle EUR, GBP, JPY)
- Handle ranges (e.g., "$10M - $20M") by taking the midpoint
- Parse formats: "5.2B", "$5,200,000,000", "5.2 billion"
- Convert NaN/null/N/A/"Not disclosed" to 0
- Return as integer

Currency Conversion (Approximate rates for this exercise):
EUR to USD: multiply by 1.1
GBP to USD: multiply by 1.27
JPY to USD: divide by 150

2. Date Normalization - Clean the "published_date" column:
- Handle multiple date formats (ISO, US, EU formats)
- Extract year, quarter, month for analysis
- Return as datetime object
- Handle edge cases (invalid dates, missing values)

3. Category Standardization - Normalize the "category" column:
- Map similar categories (e.g., "AI/ML", "Artificial Intelligence", "Machine Learning" → "AI_ML")
- Create a consistent taxonomy (provide mapping in your code)

4. Company Metadata Integration & Validation

a. Company Name Validation
i. Validate the company names in articles exist in the metadata
ii. Log or flag articles with companies not found in metadata
iii. Consider fuzzy matching for slight variations (e.g., "Amazon Web Services" vs "AWS")

b. Metadata Enrichment
i. Join company metadata in `company_metadata.json` to articles by company name
ii. Add derived fields: `company_age`: Calculate age based on `founded_year` and article `published_date`, `company_size_category`:
iii. Categorize by employee_count (e.g., "Small" < 10K, "Medium" 10K-30K, "Large" > 30K)
iv. Include all metadata fields in the final output

Industry-Based Filtering
i. Use the `industry` field from metadata as an additional filter option
ii. The metadata contains industries like "AI/ML", "Data Analytics", "Cloud Computing", etc.
iii. Consider both article `category` AND company `industry` when filtering with the company metadata section

## Deliverables

1. Code Implementation
- Put all code into the pipeline subdirectory
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
- How you handled edge cases in data cleaning
- Trade-offs you made (performance vs. accuracy)
- What you would improve with more time

requirements.txt:
- All dependencies with versions

3. Output Files
- `ai_articles_enriched.csv` - The filtered and enriched dataset 

## Constraints

- **Python 3.10+.**
- **Recommended Libraries:** standard library preferred. pandas duckdb numpy scikit-learn sentence-transformers pyarrow

## Evaluation criteria

Technical Excellence (65%)
- Code quality and organization
- Efficient data processing

Data Engineering Best Practices (20%)
- Data validation and quality checks
- Clean data transformations

Documentation (15%)
- Clear README with working instructions
- Well-explained decisions in EXPLAIN.md
