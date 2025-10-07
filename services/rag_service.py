import os
import logging
from functools import lru_cache
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.vectorstores import FAISS  # 🔁 جایگزینی Chroma با FAISS

# مسیر دیتابیس ذخیره‌شده
VECTOR_DIR = "vectorstore"
FAISS_INDEX_PATH = os.path.join(VECTOR_DIR, "faiss_index")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@lru_cache(maxsize=1)
def get_rag_chain():
    """
    Load the RAG chain from the FAISS vector database.
    Uses the embeddings and persisted vectorstore for retrieval.
    The result is cached to avoid re-loading on every request.
    """
    embeddings = OpenAIEmbeddings()

    try:
        if not os.path.exists(FAISS_INDEX_PATH):
            logger.error("Vector database not found at '%s'", FAISS_INDEX_PATH)
            return None

        vector_store = FAISS.load_local(FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)# 🔁 لود FAISS
        retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 5})

        # 📝 پرامپت RAG به زبان فارسی
        rag_prompt = ChatPromptTemplate.from_template(
            """براساس اطلاعات زیر پاسخ کاربر را بده. پاسخ‌ها دقیق و به فارسی باشند.
Context: {context}
Question: {input}
Answer:"""
        )

        llm = ChatOpenAI(model=os.getenv("MODEL", "gpt-4o-mini"), temperature=0)
        document_chain = create_stuff_documents_chain(llm, rag_prompt)

        # 🔗 ساخت زنجیره RAG
        chain = create_retrieval_chain(retriever, document_chain)
        logger.info("RAG chain loaded and cached from %s", FAISS_INDEX_PATH)
        return chain

    except Exception as e:
        logger.exception("Error loading RAG chain: %s", e)
        return None


@lru_cache(maxsize=1)
def get_vector_retriever(k: int = 5):
    """
    Load and return a FAISS retriever for direct retrieval of Documents.
    Cached so repeated calls are cheap.
    """
    embeddings = OpenAIEmbeddings()

    try:
        if not os.path.exists(FAISS_INDEX_PATH):
            logger.error("Vector database not found at '%s'", FAISS_INDEX_PATH)
            return None

        vector_store = FAISS.load_local(FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
        retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": k})
        logger.info("FAISS retriever created (k=%d) from %s", k, FAISS_INDEX_PATH)
        return retriever

    except Exception as e:
        logger.exception("Error loading FAISS retriever: %s", e)
        return None
