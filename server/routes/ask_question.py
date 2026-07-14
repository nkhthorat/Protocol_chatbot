from fastapi import APIRouter, Form
from fastapi.responses import JSONResponse
from modules.llm import get_llm_chain
from modules.query_handlers import query_chain
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pinecone import Pinecone
from pydantic import Field
from typing import List, Optional
from logger import logger
import os

router=APIRouter()

RETRIEVAL_TOP_K = 10

CASUAL_RESPONSES = {
    "hi": "Hi! Upload a clinical protocol PDF, then ask me questions about it.",
    "hello": "Hello! I can help answer questions from your uploaded protocol documents.",
    "hey": "Hey! Ask me anything about the uploaded PDFs.",
    "thanks": "You're welcome.",
    "thank you": "You're welcome.",
}


def get_casual_response(question: str) -> Optional[str]:
    normalized_question = question.strip().lower().rstrip("!.?")
    return CASUAL_RESPONSES.get(normalized_question)


@router.post("/ask/")
async def ask_question(question: str = Form(...)):
    try:
        logger.info(f"user query: {question}")

        casual_response = get_casual_response(question)
        if casual_response:
            logger.info("casual message handled without retrieval")
            return {"response": casual_response, "sources": []}

        # Embed model + Pinecone setup
        pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
        index = pc.Index(os.environ["PINECONE_INDEX_NAME"])
        embed_model = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")
        embedded_query = embed_model.embed_query(question)
        res = index.query(vector=embedded_query, top_k=RETRIEVAL_TOP_K, include_metadata=True)

        docs = [
            Document(
                page_content=match["metadata"].get("text", ""),
                metadata={
                    **match["metadata"],
                    "score": match.get("score"),
                    "vector_id": match.get("id"),
                }
            ) for match in res["matches"]
        ]

        class SimpleRetriever(BaseRetriever):
            tags: Optional[List[str]] = Field(default_factory=list)
            metadata: Optional[dict] = Field(default_factory=dict)

            def __init__(self, documents: List[Document]):
                super().__init__()
                self._docs = documents

            def _get_relevant_documents(self, query: str) -> List[Document]:
                return self._docs

        retriever = SimpleRetriever(docs)
        chain = get_llm_chain(retriever)
        #new code 
        
        result = query_chain(chain, question)

        logger.info("query successful")
        return result

    except Exception as e:
        logger.exception("Error processing question")
        return JSONResponse(status_code=500, content={"error": str(e)})
