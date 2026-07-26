# app/services/sql_generator.py
import os
from typing import List, Union
from pydantic import BaseModel, Field
import instructor
from dotenv import load_dotenv

load_dotenv()

# --- Output Schemas ---

class SQLGenerationResult(BaseModel):
    """Schema returned when a query can be confidently generated."""
    sql_query: str = Field(
        description="Valid executable SQL query matching the user request."
    )
    explanation: str = Field(
        description="A clear step-by-step natural language explanation of what this query does."
    )
    tables_accessed: List[str] = Field(
        description="List of table names accessed in this query."
    )
    confidence_score: float = Field(
        description="Self-evaluated confidence score between 0.0 and 1.0."
    )

class QueryInterpretation(BaseModel):
    interpretation: str = Field(description="Description of what this interpretation assumes.")
    example_query_idea: str = Field(description="Brief explanation of how the SQL would differ.")

class ClarificationRequest(BaseModel):
    """Schema returned when the user's question is too ambiguous to generate a single query safely."""
    is_ambiguous: bool = Field(default=True, description="Always set to True if asking for clarification.")
    ambiguity_reason: str = Field(description="Detailed explanation of why the question is ambiguous.")
    possible_interpretations: List[QueryInterpretation] = Field(
        description="List of possible business or schema interpretations."
    )

# Unified union output model
SQLResponse = Union[SQLGenerationResult, ClarificationRequest]


# --- Generator Service ---

class SQLGenerator:
    def __init__(self, model_name: str = "google/gemini-3.5-flash-lite"):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY missing in .env file.")
        
        # Instructor's unified provider loader
        self.client = instructor.from_provider(model_name, api_key=api_key)
        self.model_name = model_name

    def _build_prompt(self, user_query: str, filtered_schema_text: str) -> str:
        few_shots = """
--- FEW-SHOT EXAMPLES ---
Example 1:
Question: What are the names of customers in North America?
SQL: SELECT name FROM customers WHERE region = 'North America';

Example 2:
Question: How many products were ordered in total?
SQL: SELECT SUM(quantity) AS total_products_ordered FROM orders;

Example 3:
Question: List all sales with customer name and product category.
SQL: SELECT c.name, p.category, o.total_amount FROM orders o JOIN customers c ON o.customer_id = c.customer_id JOIN products p ON o.product_id = p.product_id;
------------------------
"""
        return f"""
You are an expert database AI. Your task is to generate valid SQL queries based strictly on the provided schema.

DATABASE SCHEMA:
{filtered_schema_text}

{few_shots}

INSTRUCTIONS:
1. Generate SQL queries ONLY using tables and columns defined in the provided schema.
2. If the user question is clear, generate the SQL along with explanation and table list.
3. IF THE QUESTION IS AMBIGUOUS (e.g., terms like "sales" or "revenue" could refer to multiple different columns/aggregations without clear context), return a ClarificationRequest listing the interpretations instead of guessing.

USER QUESTION: {user_query}
"""

    def generate_sql(self, user_query: str, filtered_schema_text: str) -> SQLResponse:
        prompt = self._build_prompt(user_query, filtered_schema_text)
        
        # Unified creation method
        response = self.client.create(
            response_model=SQLResponse,
            messages=[
                {"role": "system", "content": "You are a precise, schema-aware SQL generator."},
                {"role": "user", "content": prompt}
            ]
        )
        return response


# --- Test Execution Block ---
if __name__ == "__main__":
    from app.services.schema_extractor import SchemaExtractor
    from app.services.schema_filter import SchemaFilter

    extractor = SchemaExtractor("sqlite:///./test_db.db")
    raw_schema = extractor.extract_full_schema()
    schema_filter = SchemaFilter(raw_schema)
    
    generator = SQLGenerator()

    # Test Case 1: Standard Clear Question
    query1 = "What is the total quantity of electronics items ordered by Alice?"
    filtered_schema1 = schema_filter.filter_schema(query1)
    schema_text1 = extractor.format_schema_for_prompt(filtered_schema1)
    
    print(f"\n==================== TEST 1: CLEAR QUERY ====================")
    print(f"User Question: '{query1}'")
    result1 = generator.generate_sql(query1, schema_text1)
    
    if isinstance(result1, SQLGenerationResult):
        print(f"\nGenerated SQL:\n{result1.sql_query}")
        print(f"\nExplanation:\n{result1.explanation}")
        print(f"Tables Used: {result1.tables_accessed}")
        print(f"Confidence Score: {result1.confidence_score}")
    
    # Test Case 2: Ambiguous Question
    query2 = "Show me the revenue performance."
    filtered_schema2 = schema_filter.filter_schema(query2)
    schema_text2 = extractor.format_schema_for_prompt(filtered_schema2)
    
    print(f"\n==================== TEST 2: AMBIGUOUS QUERY ====================")
    print(f"User Question: '{query2}'")
    result2 = generator.generate_sql(query2, schema_text2)
    
    if isinstance(result2, ClarificationRequest):
        print(f"\n[Ambiguity Detected]")
        print(f"Reason: {result2.ambiguity_reason}")
        print("Interpretations:")
        for interp in result2.possible_interpretations:
            print(f" - {interp.interpretation} ({interp.example_query_idea})")