
import os
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore

load_dotenv()

def main():
    if not os.getenv("PINECONE_API_KEY"):
        raise ValueError("Missing PINECONE_API_KEY in your .env file!")
        
    print("Initializing local embedding engine...")
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    log_path = "HDFS_2k.log"
    if not os.path.exists(log_path):
        raise FileNotFoundError(f"Could not find {log_path}. Did you run the wget command?")
        
    print(f"Reading raw system logs from {log_path}...")
    

    loader = TextLoader(file_path=log_path, encoding="utf-8")
    raw_documents = loader.load()
    print("Log file loaded into memory.")

    print("Chunking historical logs into semantic blocks...")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=300)
    docs = text_splitter.split_documents(raw_documents)
    print(f"Generated {len(docs)} text chunks for upload.")

    index_name = os.getenv("PINECONE_INDEX_NAME", "archguard-logs")
    print(f"Streaming vectors to Pinecone index: '{index_name}'...")
    

    PineconeVectorStore.from_documents(
        docs,
        embeddings,
        index_name=index_name
    )
    
    print("SUCCESS: Your raw system logs are now fully searchable in the cloud!")
if __name__ == "__main__":
    main()