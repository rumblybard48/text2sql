# app/services/verifier.py
import os
import instructor
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

class BackTranslationResult(BaseModel):
    reconstructed_question: str = Field(
        description="A clear, plain-English summary of what this SQL query actually measures/returns."
    )
    alignment_score: float = Field(
        description="Semantic match score (0.0 to 1.0) comparing reconstructed intent to original user question."
    )
    divergence_reason: Optional[str] = Field(
        default=None, 
        description="Explanation if the reconstructed question diverges from the original."
    )

class SanityCheckResult(BaseModel):
    passed: bool
    warnings: List[str] = Field(default_factory=list)

class SQLVerifier:
    def __init__(self, model_name: str = "google/gemini-3.5-flash-lite"):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY missing in .env file.")
        
        self.client = instructor.from_provider(model_name, api_key=api_key)

    def back_translate(self, original_question: str, generated_sql: str) -> BackTranslationResult:
        """Translates generated SQL back into English and measures intent alignment."""
        prompt = f"""
You are an expert SQL auditor. Your job is to reverse-engineer a SQL query back into a plain English question and assess if it matches the original user intent.

ORIGINAL USER QUESTION: "{original_question}"
GENERATED SQL QUERY:
{generated_sql}

INSTRUCTIONS:
1. Summarize in 1 sentence what question this exact SQL query actually answers (reconstructed_question).
2. Compare the reconstructed question with the original user question.
3. Assign an alignment_score between 0.0 (completely different intent) and 1.0 (exact semantic match).
4. If the score is below 0.8, explain the divergence_reason (e.g., missing filters, wrong aggregation, wrong table joined).
"""
        return self.client.create(
            response_model=BackTranslationResult,
            messages=[{"role": "user", "content": prompt}]
        )

    def perform_sanity_checks(self, data: List[Dict[str, Any]], columns: List[str]) -> SanityCheckResult:
        """Audits execution results for anomaly red flags (NULL-heavy columns, empty sets)."""
        warnings = []
        
        # Check 1: Empty Result Set
        if not data:
            return SanityCheckResult(
                passed=True, 
                warnings=["Query executed successfully but returned 0 rows. Verify filter criteria."]
            )

        row_count = len(data)

        # Check 2: High NULL Ratio across columns (Indicates improper JOIN condition)
        for col in columns:
            null_count = sum(1 for row in data if row.get(col) is None)
            null_ratio = null_count / row_count
            if null_ratio > 0.5 and row_count > 1:
                warnings.append(
                    f"Column '{col}' has {round(null_ratio * 100, 1)}% NULL values. Possible unmatched LEFT JOIN."
                )

        # Check 3: Suspiciously huge single-row aggregated NULL
        if row_count == 1:
            first_row = data[0]
            if all(val is None for val in first_row.values()):
                warnings.append("Aggregation returned NULL across all columns.")

        return SanityCheckResult(
            passed=len(warnings) == 0,
            warnings=warnings
        )


# Test Verification Directly
if __name__ == "__main__":
    verifier = SQLVerifier()

    # Test Case: Correct SQL vs Minor Misalignment
    orig_q = "What is the total quantity of electronics items ordered by Alice?"
    
    # Intentionally slightly misaligned SQL (missing customer filter)
    flawed_sql = "SELECT SUM(quantity) FROM orders o JOIN products p ON o.product_id = p.product_id WHERE p.category = 'Electronics';"

    print("--- 1. Testing Back-Translation ---")
    translation = verifier.back_translate(orig_q, flawed_sql)
    print(f"Original Question: {orig_q}")
    print(f"Reconstructed:     {translation.reconstructed_question}")
    print(f"Alignment Score:   {translation.alignment_score}")
    print(f"Divergence Reason: {translation.divergence_reason}")

    print("\n--- 2. Testing Sanity Check ---")
    mock_data = [
        {"name": "Alice", "product_name": None, "total_amount": 1200.0},
        {"name": "Alice", "product_name": None, "total_amount": 300.0}
    ]
    sanity = verifier.perform_sanity_checks(mock_data, ["name", "product_name", "total_amount"])
    print(f"Passed:   {sanity.passed}")
    print(f"Warnings: {sanity.warnings}")