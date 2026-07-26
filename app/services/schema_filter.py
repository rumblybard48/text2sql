# app/services/schema_filter.py
import chromadb
from chromadb.utils import embedding_functions
from app.services.schema_extractor import SchemaExtractor

class SchemaFilter:
    def __init__(self, schema_data: dict, collection_name: str = "db_schema"):
        self.schema_data = schema_data
        
        # Initialize an in-memory Chroma client
        self.client = chromadb.Client()
        
        # Use default lightweight SentenceTransformer embeddings
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        
        # Create or recreate collection
        try:
            self.client.delete_collection(name=collection_name)
        except Exception:
            pass
            
        self.collection = self.client.create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn
        )
        
        # Index table descriptions into the vector store
        self._index_schema()

    def _index_schema(self):
        """Converts each table's schema into text and indexes it in ChromaDB."""
        documents = []
        metadatas = []
        ids = []

        for table_name, details in self.schema_data.items():
            cols = [col["name"] for col in details["columns"]]
            # Build a rich semantic description of the table for embedding
            doc_text = f"Table name: {table_name}. Columns: {', '.join(cols)}."
            
            documents.append(doc_text)
            metadatas.append({"table_name": table_name})
            ids.append(f"table_{table_name}")

        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    def filter_schema(self, query: str, top_k: int = 2) -> dict:
        """Retrieves only the top-K relevant tables matching the user question."""
        results = self.collection.query(
            query_texts=[query],
            n_results=min(top_k, len(self.schema_data))
        )
        
        # Extract matched table names from vector metadata
        matched_tables = [
            meta["table_name"] 
            for meta_list in results["metadatas"] 
            for meta in meta_list
        ]
        
        # Construct a filtered schema dictionary containing only matched tables
        filtered_schema = {
            table: self.schema_data[table] 
            for table in matched_tables 
            if table in self.schema_data
        }
        
        return filtered_schema


# Test execution block
if __name__ == "__main__":
    # 1. Extract schema
    extractor = SchemaExtractor("sqlite:///./test_db.db")
    raw_schema = extractor.extract_full_schema()
    
    # 2. Index schema into ChromaDB
    schema_filter = SchemaFilter(raw_schema)
    
    # 3. Test vector filtering with a targeted question
    test_query = "What is the total money spent by Alice on electronics?"
    filtered_schema = schema_filter.filter_schema(test_query, top_k=2)
    
    # 4. Print filtered output
    formatted_filtered = extractor.format_schema_for_prompt(filtered_schema)
    print(f"--- Query: '{test_query}' ---")
    print("\n--- Relevant Filtered Schema ---\n")
    print(formatted_filtered)