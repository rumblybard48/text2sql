# app/services/executor.py
import time
import pandas as pd
from sqlalchemy import create_engine, text
from pydantic import BaseModel, Field
from typing import Any, List, Dict, Optional

class ExecutionResult(BaseModel):
    success: bool
    data: List[Dict[str, Any]] = Field(default_factory=list, description="Raw rows returned as dictionaries")
    columns: List[str] = Field(default_factory=list, description="Column names")
    row_count: int = 0
    execution_time_ms: float = 0.0
    error_message: Optional[str] = None

class SQLExecutor:
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)

    def execute_query(self, sql: str) -> ExecutionResult:
        """Executes SQL inside a read-only transaction and formats results into a DataFrame structure."""
        start_time = time.time()
        
        try:
            # Open transaction connection
            with self.engine.connect() as connection:
                # Wrap in read-only transaction
                with connection.begin():
                    # Execute using pandas for clean DataFrame serialization
                    df = pd.read_sql_query(text(sql), connection)
                    
            elapsed_time_ms = round((time.time() - start_time) * 1000, 2)
            
            return ExecutionResult(
                success=True,
                data=df.to_dict(orient="records"),
                columns=list(df.columns),
                row_count=len(df),
                execution_time_ms=elapsed_time_ms,
                error_message=None
            )
            
        except Exception as e:
            elapsed_time_ms = round((time.time() - start_time) * 1000, 2)
            return ExecutionResult(
                success=False,
                data=[],
                columns=[],
                row_count=0,
                execution_time_ms=elapsed_time_ms,
                error_message=str(e)
            )


# Test Execution Engine
if __name__ == "__main__":
    executor = SQLExecutor("sqlite:///./test_db.db")
    
    # Test safe query execution
    sample_sql = "SELECT c.name, p.product_name, o.total_amount FROM orders o JOIN customers c ON o.customer_id = c.customer_id JOIN products p ON o.product_id = p.product_id LIMIT 500"
    result = executor.execute_query(sample_sql)
    
    print("\n==================== QUERY EXECUTION RESULT ====================")
    print(f"Success: {result.success}")
    print(f"Execution Time: {result.execution_time_ms} ms")
    print(f"Rows Returned: {result.row_count}")
    print(f"Columns: {result.columns}")
    print("Data Preview:")
    for row in result.data:
        print(f" - {row}")