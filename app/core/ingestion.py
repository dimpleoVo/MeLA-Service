import logging
import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataIngestionEngine:
    def __init__(self):
        """
        初始化数据处理引擎
        """
        # 定义切分器
        # chunk_size=500: 既能包含足够上下文，又不会太长导致 Embedding 丢失细节
        # chunk_overlap=50: 关键参数！保留重叠部分，防止一句话被切两半导致语义丢失
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", "。", "！", "？", " ", ""]
        )

    def process_pdf(self, file_path: str):
        """
        ETL 核心流程：Load (加载) -> Split (切分)
        """
        logger.info(f"开始处理文件: {file_path}")

        try:
            # 1. Load: 使用 pypdf 加载 PDF
            loader = PyPDFLoader(file_path)
            raw_docs = loader.load()
            logger.info(f"PDF 加载成功，共 {len(raw_docs)} 页")

            # 2. Split: 执行语义切分
            chunks = self.text_splitter.split_documents(raw_docs)
            logger.info(f"切分完成，共生成 {len(chunks)} 个语义块")

            # 3. Extract: 提取纯文本和元数据(Metadata)
            # metadata 包含页码等信息，方便后续引用溯源
            texts = [doc.page_content for doc in chunks]
            metadatas = [doc.metadata for doc in chunks]

            return texts, metadatas

        except Exception as e:
            logger.error(f"处理 PDF 失败: {e}")
            raise e


# 单例模式
ingestion_service = DataIngestionEngine()