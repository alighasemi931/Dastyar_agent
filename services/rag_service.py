import streamlit as st
import os
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.vectorstores import Chroma

# مسیر وکتور دیتابیس ساخته‌شده
CHROMA_DIR = "vectorstore"

@st.cache_resource
def get_rag_chain():
    """
    Load the RAG chain from the Chroma vector database.
    Uses the embeddings and persisted vectorstore for retrieval.
    """
    # Load embeddings and vectorstore
    embeddings = OpenAIEmbeddings()
    
    try:
        # اگر دیتابیس وکتور وجود نداشت، هشدار بده
        if not os.path.exists(CHROMA_DIR):
            st.error(f"❌ وکتور دیتابیس در مسیر '{CHROMA_DIR}' یافت نشد.")
            return None

        vector_store = Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)
        retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 5})

        # Prompt template برای RAG
        rag_prompt = ChatPromptTemplate.from_template(
            """بر اساس اطلاعات زیر پاسخ کاربر را بده. پاسخ‌ها دقیق و به فارسی باشند.
Context: {context}
Question: {input}
Answer:"""
        )
        
        llm = ChatOpenAI(model=os.getenv("MODEL", "gpt-4o-mini"), temperature=0)
        document_chain = create_stuff_documents_chain(llm, rag_prompt)

        # ایجاد زنجیره کامل RAG
        return create_retrieval_chain(retriever, document_chain)
    
    except Exception as e:
        st.error(f"❌ خطا در بارگذاری RAG chain: {e}")
        return None
