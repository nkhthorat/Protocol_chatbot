import os
import time
from pathlib import Path
from dotenv import load_dotenv
from tqdm.auto import tqdm
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential
from pinecone import Pinecone, ServerlessSpec
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_google_genai._common import GoogleGenerativeAIError

load_dotenv()

GOOGLE_API_KEY=os.getenv("GOOGLE_API_KEY")
PINECONE_API_KEY=os.getenv("PINECONE_API_KEY")
PINECONE_ENV="us-east-1"
PINECONE_INDEX_NAME="medicalindex"

os.environ["GOOGLE_API_KEY"]=GOOGLE_API_KEY

UPLOAD_DIR="./uploaded_docs"
os.makedirs(UPLOAD_DIR,exist_ok=True)

# Google's free-tier embedding quota is limited per minute, so we embed and
# upsert in small batches with retries instead of one giant call per file.
EMBED_BATCH_SIZE = 25
UPSERT_BATCH_SIZE = 100


def _is_rate_limit_error(exc: BaseException) -> bool:
    return isinstance(exc, GoogleGenerativeAIError) and "RESOURCE_EXHAUSTED" in str(exc)


@retry(
    retry=retry_if_exception(_is_rate_limit_error),
    wait=wait_exponential(multiplier=2, min=5, max=60),
    stop=stop_after_attempt(6),
    reraise=True,
)
def _embed_batch(embed_model, batch_texts):
    return embed_model.embed_documents(batch_texts)


# initialize pinecone instance
pc=Pinecone(api_key=PINECONE_API_KEY)
spec=ServerlessSpec(cloud="aws",region=PINECONE_ENV)
existing_indexes=[i["name"] for i in pc.list_indexes()]


if PINECONE_INDEX_NAME not in existing_indexes:
    pc.create_index(
        name=PINECONE_INDEX_NAME,
        dimension=3072,
        metric="dotproduct",
        spec=spec
    )
    while not pc.describe_index(PINECONE_INDEX_NAME).status["ready"]:
        time.sleep(1)


index=pc.Index(PINECONE_INDEX_NAME)

# load,split,embed and upsert pdf docs content

def load_vectorstore(uploaded_files):
    embed_model = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")
    file_paths = []

    for file in uploaded_files:
        save_path = Path(UPLOAD_DIR) / file.filename
        with open(save_path, "wb") as f:
            f.write(file.file.read())
        file_paths.append(str(save_path))

    for file_path in file_paths:
        loader = PyPDFLoader(file_path)
        documents = loader.load()

        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        chunks = splitter.split_documents(documents)

        texts = [chunk.page_content for chunk in chunks]
        metadatas = [
            {
                **chunk.metadata,
                "text": chunk.page_content
            }
            for chunk in chunks
        ]
        ids = [f"{Path(file_path).stem}-{i}" for i in range(len(chunks))]

        print(f"🔍 Embedding {len(texts)} chunks in batches of {EMBED_BATCH_SIZE}...")
        with tqdm(total=len(texts), desc="Embedding + upserting") as progress:
            for start in range(0, len(texts), EMBED_BATCH_SIZE):
                end = start + EMBED_BATCH_SIZE
                batch_texts = texts[start:end]
                batch_ids = ids[start:end]
                batch_metadatas = metadatas[start:end]

                batch_embeddings = _embed_batch(embed_model, batch_texts)

                for upsert_start in range(0, len(batch_embeddings), UPSERT_BATCH_SIZE):
                    upsert_end = upsert_start + UPSERT_BATCH_SIZE
                    index.upsert(vectors=zip(
                        batch_ids[upsert_start:upsert_end],
                        batch_embeddings[upsert_start:upsert_end],
                        batch_metadatas[upsert_start:upsert_end],
                    ))

                progress.update(len(batch_texts))

        print(f"✅ Upload complete for {file_path}")