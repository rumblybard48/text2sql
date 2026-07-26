# app/services/guardrails.py
import re
import sqlparse
from sqlparse.tokens import DDL, DML, Keyword
from pydantic import BaseModel, Field

class GuardrailValidationResult(BaseModel):
    is_safe: bool = Field(description="True if query passed all security checks, False otherwise.")
    sanitized_sql: str = Field(description="Sanitized SQL query with safety transforms applied (e.g., forced LIMIT).")
    violation_reason: str = Field(default="", description="Reason for rejection if is_safe is False.")

class SQLGuardrail:
    FORBIDDEN_KEYWORDS = {
        "DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "TRUNCATE",
        "CREATE", "GRANT", "REVOKE", "EXEC", "EXECUTE", "VACUUM"
    }

    def __init__(self, max_row_limit: int = 1000, max_subquery_depth: int = 3):
        self.max_row_limit = max_row_limit
        self.max_subquery_depth = max_subquery_depth

    def validate_and_sanitize(self, raw_sql: str) -> GuardrailValidationResult:
        """Runs multi-layered checks against raw SQL string."""
        clean_sql = raw_sql.strip().rstrip(";")

        # 1. Reject Multiple Statements (SQL Injection Prevention)
        parsed_statements = sqlparse.parse(clean_sql)
        if len(parsed_statements) > 1:
            return GuardrailValidationResult(
                is_safe=False,
                sanitized_sql=raw_sql,
                violation_reason="Multiple SQL statements detected. Execution blocked for security."
            )

        statement = parsed_statements[0]

        # 2. Token / AST Keyword Inspection for Mutating DDL / DML
        for token in statement.flatten():
            token_val = token.value.upper()
            if token_val in self.FORBIDDEN_KEYWORDS:
                return GuardrailValidationResult(
                    is_safe=False,
                    sanitized_sql=raw_sql,
                    violation_reason=f"Forbidden operation '{token_val}' detected. Only read-only SELECT queries are allowed."
                )

        # 3. Must be a SELECT statement
        first_token = statement.get_type()
        if first_token.upper() != "SELECT":
            return GuardrailValidationResult(
                is_safe=False,
                sanitized_sql=raw_sql,
                violation_reason="Query is not a SELECT statement."
            )

        # 4. Check Subquery Depth (Prevent Denial of Service / Deep Recursion)
        depth = self._check_subquery_depth(clean_sql)
        if depth > self.max_subquery_depth:
            return GuardrailValidationResult(
                is_safe=False,
                sanitized_sql=raw_sql,
                violation_reason=f"Subquery depth ({depth}) exceeds maximum allowed depth ({self.max_subquery_depth})."
            )

        # 5. Enforce Row Limits (Force LIMIT N)
        sanitized_sql = self._enforce_limit(clean_sql)

        return GuardrailValidationResult(
            is_safe=True,
            sanitized_sql=sanitized_sql,
            violation_reason=""
        )

    def _check_subquery_depth(self, sql: str) -> int:
        """Measures maximum depth of nested parentheses containing SELECT."""
        max_depth = 0
        current_depth = 0
        for char in sql:
            if char == '(':
                current_depth += 1
                if current_depth > max_depth:
                    max_depth = current_depth
            elif char == ')':
                current_depth = max(0, current_depth - 1)
        return max_depth

    def _enforce_limit(self, sql: str) -> str:
        """Appends or clamps a LIMIT clause to prevent huge result payload overloads."""
        limit_match = re.search(r'\bLIMIT\s+(\d+)', sql, re.IGNORECASE)
        if limit_match:
            existing_limit = int(limit_match.group(1))
            if existing_limit > self.max_row_limit:
                # Clamp down limit
                sql = re.sub(r'\bLIMIT\s+\d+', f'LIMIT {self.max_row_limit}', sql, flags=re.IGNORECASE)
        else:
            # Append limit if missing
            sql = f"{sql} LIMIT {self.max_row_limit}"
        return sql


# Test Guardrails directly
if __name__ == "__main__":
    guard = SQLGuardrail(max_row_limit=500)

    test_queries = [
        "SELECT * FROM customers",                                   # Should pass (adds LIMIT 500)
        "SELECT * FROM customers LIMIT 5000",                       # Should pass (clamps LIMIT to 500)
        "DELETE FROM customers WHERE customer_id = 1",              # Should fail (DELETE detected)
        "SELECT * FROM customers; DROP TABLE orders;",              # Should fail (Multi-statement)
        "SELECT * FROM (SELECT * FROM (SELECT * FROM (SELECT * FROM products)))" # Should fail (Depth > 3)
    ]

    print("--- GUARDRAIL TEST SUITE ---")
    for q in test_queries:
        res = guard.validate_and_sanitize(q)
        print(f"\nRaw SQL: {q}")
        print(f"Safe: {res.is_safe}")
        if res.is_safe:
            print(f"Sanitized SQL: {res.sanitized_sql}")
        else:
            print(f"Violation: {res.violation_reason}")