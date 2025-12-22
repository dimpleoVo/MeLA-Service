import chromadb
from chromadb.utils import embedding_functions
import uuid
import logging

# 1. 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAG_Engine:
    def __init__(self, collection_name: str = "lumos_knowledge_base"):
        """
        初始化向量数据库
        """
        # 持久化存储路径 (生产环境会挂载到 Docker Volume)
        self.client = chromadb.PersistentClient(path="./chroma_db_data")

        # 使用默认的 Embedding 模型 (all-MiniLM-L6-v2)
        # 如果是生产环境，这里会换成 OpenAIEmbeddingFunction
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()

        # 获取或创建集合 (类似于 SQL 里的 Table)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn
        )


    def add_documents(self, documents: list[str], metadatas: list[dict] = None):
        """
        数据入库 (Ingestion)
        """
        if not documents:
            return 0

        ids = [str(uuid.uuid4()) for _ in documents]

        # 存入向量库：它会自动把 text 转成 vector
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        logger.info(f"成功入库 {len(documents)} 条文档")
        return len(documents)

    def search(self, query: str, top_k: int = 3):
        """
        语义检索 (Retrieval)
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k
        )

        # 简单的结果解析
        # results['documents'] 是一个列表的列表 [[doc1, doc2]]
        return {
            "query": query,
            "results": results['documents'][0],
            "distances": results['distances'][0]  # 距离越小越相似
        }


# 单例模式：为了复用连接
rag_service = RAG_Engine()