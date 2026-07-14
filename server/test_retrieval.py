import os
from dotenv import load_dotenv
from pinecone import Pinecone
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(INDEX_NAME)

embed = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

query = "what is diabetes?"   # change this

vector = embed.embed_query(query)

print("\nVector length:", len(vector))

res = index.query(
    vector=vector,
    top_k=3,
    include_metadata=True
)

print("\n===== TOP K RESULTS =====\n")

for i, match in enumerate(res["matches"]):
    print(f"\n--- DOC {i} ---")
    print("Score:", match["score"])
    print("Text:", match["metadata"].get("text", "")[:500])
    print("Metadata:", match["metadata"])