# app/services/scoring.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any

class ConfidenceBreakdown(BaseModel):
    syntax_and_guardrails: float = Field(description="Score for passing SQL syntax and security checks (0-100)")
    alignment_score: float = Field(description="Score for back-translation semantic match (0-100)")
    sanity_check_score: float = Field(description="Score for passing data anomaly checks (0-100)")
    execution_success: float = Field(description="Score for execution without runtime errors (0-100)")
    
    final_confidence_score: float = Field(description="Weighted combined confidence score (0-100)")
    confidence_level: str = Field(description="HIGH, MEDIUM, or LOW")

class ConfidenceScorer:
    # Defined Weights
    WEIGHT_GUARDRAILS = 0.25
    WEIGHT_ALIGNMENT = 0.40
    WEIGHT_SANITY = 0.20
    WEIGHT_EXECUTION = 0.15

    @classmethod
    def calculate_score(
        self,
        is_safe: bool,
        execution_success: bool,
        alignment_score_0_to_1: float,
        sanity_passed: bool,
        sanity_warning_count: int
    ) -> ConfidenceBreakdown:
        
        # 1. Guardrail Score
        guardrail_pts = 100.0 if is_safe else 0.0
        
        # 2. Execution Score
        execution_pts = 100.0 if execution_success else 0.0
        
        # 3. Back-Translation Alignment Score
        alignment_pts = min(100.0, max(0.0, alignment_score_0_to_1 * 100.0))
        
        # 4. Sanity Score
        if not sanity_passed and sanity_warning_count > 0:
            sanity_pts = max(30.0, 100.0 - (sanity_warning_count * 25.0))
        else:
            sanity_pts = 100.0

        # Weighted Sum
        final_score = round(
            (guardrail_pts * self.WEIGHT_GUARDRAILS) +
            (alignment_pts * self.WEIGHT_ALIGNMENT) +
            (sanity_pts * self.WEIGHT_SANITY) +
            (execution_pts * self.WEIGHT_EXECUTION),
            1
        )

        # Confidence Threshold Categorization
        if final_score >= 85.0:
            level = "HIGH"
        elif final_score >= 65.0:
            level = "MEDIUM"
        else:
            level = "LOW"

        return ConfidenceBreakdown(
            syntax_and_guardrails=guardrail_pts,
            alignment_score=round(alignment_pts, 1),
            sanity_check_score=round(sanity_pts, 1),
            execution_success=execution_pts,
            final_confidence_score=final_score,
            confidence_level=level
        )


# Test Scorer
if __name__ == "__main__":
    result = ConfidenceScorer.calculate_score(
        is_safe=True,
        execution_success=True,
        alignment_score_0_to_1=0.92,
        sanity_passed=True,
        sanity_warning_count=0
    )
    print("--- CONFIDENCE SCORE BREAKDOWN ---")
    print(f"Final Score:      {result.final_confidence_score}% ({result.confidence_level})")
    print(f" - Guardrails:    {result.syntax_and_guardrails}/100")
    print(f" - Alignment:     {result.alignment_score}/100")
    print(f" - Data Sanity:   {result.sanity_check_score}/100")
    print(f" - Execution:     {result.execution_success}/100")