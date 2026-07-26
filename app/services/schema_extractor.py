# app/services/schema_extractor.py
from sqlalchemy import create_engine, inspect

class SchemaExtractor:
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        self.inspector = inspect(self.engine)

    def extract_full_schema(self) -> dict:
        """Introspects the DB and collects tables, columns, types, and foreign keys."""
        schema_data = {}
        tables = self.inspector.get_table_names()

        for table in tables:
            columns = self.inspector.get_columns(table)
            fks = self.inspector.get_foreign_keys(table)
            pks = self.inspector.get_pk_constraint(table).get('constrained_columns', [])

            schema_data[table] = {
                "columns": [
                    {
                        "name": col["name"],
                        "type": str(col["type"]),
                        "is_primary_key": col["name"] in pks
                    }
                    for col in columns
                ],
                "foreign_keys": [
                    {
                        "constrained_columns": fk["constrained_columns"],
                        "referred_table": fk["referred_table"],
                        "referred_columns": fk["referred_columns"]
                    }
                    for fk in fks
                ]
            }
        return schema_data

    def format_schema_for_prompt(self, schema_data: dict) -> str:
        """Formats extracted schema dictionary into a readable text block for LLM prompts."""
        prompt_text = ""
        for table_name, details in schema_data.items():
            prompt_text += f"Table: {table_name}\nColumns:\n"
            for col in details["columns"]:
                pk_flag = " (Primary Key)" if col["is_primary_key"] else ""
                prompt_text += f"  - {col['name']} ({col['type']}){pk_flag}\n"
            
            if details["foreign_keys"]:
                prompt_text += "Foreign Keys:\n"
                for fk in details["foreign_keys"]:
                    prompt_text += f"  - {fk['constrained_columns']} -> {fk['referred_table']}({fk['referred_columns']})\n"
            prompt_text += "\n"
        return prompt_text.strip()

# Test runner block
if __name__ == "__main__":
    extractor = SchemaExtractor("sqlite:///./test_db.db")
    raw_schema = extractor.extract_full_schema()
    formatted_schema = extractor.format_schema_for_prompt(raw_schema)
    print("--- Extracted Schema Representation ---\n")
    print(formatted_schema)