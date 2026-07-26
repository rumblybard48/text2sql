# app/main.py
import os
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from app.services.schema_extractor import SchemaExtractor
from app.services.schema_filter import SchemaFilter
from app.services.sql_generator import SQLGenerator, SQLGenerationResult, ClarificationRequest
from app.services.guardrails import SQLGuardrail
from app.services.executor import SQLExecutor
from app.services.verifier import SQLVerifier
from app.services.scoring import ConfidenceScorer, ConfidenceBreakdown

load_dotenv()

app = FastAPI(
    title="Schema-Aware Text-to-SQL Engine",
    description="Translates English to SQL with guardrails, back-translation verification, and confidence scoring.",
    version="1.0.0"
)

# Global Service Initialization
DB_URL = os.getenv("DATABASE_URL", "sqlite:///./test_db.db")

schema_extractor = SchemaExtractor(DB_URL)
raw_schema = schema_extractor.extract_full_schema()
schema_filter = SchemaFilter(raw_schema)

sql_generator = SQLGenerator()
guardrail = SQLGuardrail(max_row_limit=1000)
executor = SQLExecutor(DB_URL)
verifier = SQLVerifier()

# In-memory history store for session logging
QUERY_HISTORY: List[Dict[str, Any]] = []


# --- Request & Response Models ---

class QueryRequest(BaseModel):
    question: str = Field(..., description="Plain English database question")

class QueryResponse(BaseModel):
    question: str
    is_ambiguous: bool = False
    ambiguity_details: Optional[Dict[str, Any]] = None
    sql_query: Optional[str] = None
    explanation: Optional[str] = None
    sanitized_sql: Optional[str] = None
    data: List[Dict[str, Any]] = Field(default_factory=list)
    columns: List[str] = Field(default_factory=list)
    row_count: int = 0
    execution_time_ms: float = 0.0
    guardrail_passed: bool = True
    guardrail_warning: Optional[str] = None
    confidence: Optional[ConfidenceBreakdown] = None
    reconstructed_question: Optional[str] = None
    sanity_warnings: List[str] = Field(default_factory=list)


# --- Endpoints ---

@app.post("/v1/query", response_model=QueryResponse)
def process_query(request: QueryRequest):
    user_q = request.question.strip()
    if not user_q:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # 1. Filter Schema
    filtered_schema = schema_filter.filter_schema(user_q, top_k=3)
    schema_text = schema_extractor.format_schema_for_prompt(filtered_schema)

    # 2. Generate Structured SQL / Ambiguity Check
    generation_output = sql_generator.generate_sql(user_q, schema_text)

    if isinstance(generation_output, ClarificationRequest):
        res = QueryResponse(
            question=user_q,
            is_ambiguous=True,
            ambiguity_details=generation_output.model_dump()
        )
        QUERY_HISTORY.append(res.model_dump())
        return res

    raw_sql = generation_output.sql_query
    explanation = generation_output.explanation

    # 3. Guardrail Middleware Validation
    guard_res = guardrail.validate_and_sanitize(raw_sql)
    
    if not guard_res.is_safe:
        # Blocked by guardrails
        score = ConfidenceScorer.calculate_score(
            is_safe=False,
            execution_success=False,
            alignment_score_0_to_1=0.0,
            sanity_passed=False,
            sanity_warning_count=1
        )
        res = QueryResponse(
            question=user_q,
            sql_query=raw_sql,
            explanation=explanation,
            guardrail_passed=False,
            guardrail_warning=guard_res.violation_reason,
            confidence=score
        )
        QUERY_HISTORY.append(res.model_dump())
        return res

    # 4. Safe Execution Layer
    exec_res = executor.execute_query(guard_res.sanitized_sql)

    # 5. Hallucination Detection & Back-Translation
    back_trans = verifier.back_translate(user_q, guard_res.sanitized_sql)
    sanity_res = verifier.perform_sanity_checks(exec_res.data, exec_res.columns)

    # 6. Confidence Scoring
    confidence_score = ConfidenceScorer.calculate_score(
        is_safe=True,
        execution_success=exec_res.success,
        alignment_score_0_to_1=back_trans.alignment_score,
        sanity_passed=sanity_res.passed,
        sanity_warning_count=len(sanity_res.warnings)
    )

    response = QueryResponse(
        question=user_q,
        is_ambiguous=False,
        sql_query=raw_sql,
        sanitized_sql=guard_res.sanitized_sql,
        explanation=explanation,
        data=exec_res.data,
        columns=exec_res.columns,
        row_count=exec_res.row_count,
        execution_time_ms=exec_res.execution_time_ms,
        guardrail_passed=True,
        confidence=confidence_score,
        reconstructed_question=back_trans.reconstructed_question,
        sanity_warnings=sanity_res.warnings
    )

    QUERY_HISTORY.append(response.model_dump())
    return response

@app.get("/v1/schema")
def get_schema():
    """Returns raw introspection representation of database."""
    return raw_schema

@app.get("/v1/history")
def get_history():
    """Returns query history for current session."""
    return QUERY_HISTORY