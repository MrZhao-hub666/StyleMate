"""
知识库加载器

使用 ChromaDB 向量数据库 + sentence-transformers 做 RAG 检索。
文本分块由纯 Python 实现，按自然段落和句子边界切分。
"""

import re
from pathlib import Path
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from app.config import CHROMA_PERSIST_DIR

KNOWLEDGE_DIR = Path(__file__).resolve().parent / "files"
MODEL_CACHE_DIR = Path.home() / ".cache" / "stylemate" / "models"


# ====== 文本分块 ======

def _split_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    按自然段落 + 句子边界分块，保持语义完整。
    """
    # 先按双换行（段落边界）切分
    paragraphs = re.split(r"\n\n+", text)
    chunks = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current) + len(para) <= chunk_size:
            current = (current + "\n\n" + para).strip()
        else:
            if current:
                chunks.append(current)
            # 如果单个段落超长，按句子切分
            if len(para) > chunk_size:
                sentences = re.split(r"(?<=[。！？；])", para)
                for s in sentences:
                    s = s.strip()
                    if not s:
                        continue
                    if len(current) + len(s) <= chunk_size:
                        current = (current + s).strip()
                    else:
                        if current:
                            chunks.append(current)
                        # 重叠：保留最后 overlap 长度的字符
                        current = current[-overlap:] if current and overlap else ""
                        current = (current + s).strip()
            else:
                current = para

    if current:
        chunks.append(current)

    return chunks


# ====== Embedding 模型 ======

def _ensure_model_downloaded() -> str:
    """通过 ModelScope 下载 embedding 模型到本地缓存，返回模型路径"""
    target_dir = MODEL_CACHE_DIR / "text2vec-base-chinese"
    target_dir.mkdir(parents=True, exist_ok=True)

    if (target_dir / "pytorch_model.bin").exists() or \
       (target_dir / "model.safetensors").exists():
        return str(target_dir)

    try:
        from modelscope import snapshot_download
    except ImportError:
        raise RuntimeError("请安装 modelscope: pip install modelscope")

    for model_id in (
        "iic/nlp_gte_sentence-embedding_chinese-base",
        "shibing624/text2vec-base-chinese",
    ):
        try:
            snapshot_download(model_id, cache_dir=str(MODEL_CACHE_DIR))
            break
        except Exception:
            continue

    # 找到下载后的模型目录
    patterns = list(MODEL_CACHE_DIR.glob("**/pytorch_model.bin")) + \
               list(MODEL_CACHE_DIR.glob("**/model.safetensors"))
    if patterns:
        return str(patterns[0].parent)
    return str(target_dir)


# ====== KnowledgeBase 类 ======

class KnowledgeBase:
    """本地知识库（ChromaDB + sentence-transformers）"""

    def __init__(self):
        self.model = None
        self.collection = None

    def _get_model(self) -> SentenceTransformer:
        if self.model is None:
            model_path = _ensure_model_downloaded()
            self.model = SentenceTransformer(model_path, device="cpu")
        return self.model

    def _get_collection(self) -> chromadb.Collection:
        if self.collection is None:
            client = chromadb.PersistentClient(
                path=str(CHROMA_PERSIST_DIR),
                settings=Settings(anonymized_telemetry=False),
            )
            self.collection = client.get_or_create_collection(
                name="stylemate_knowledge",
                metadata={"hnsw:space": "cosine"},
            )
        return self.collection

    def load_documents(self) -> list[dict]:
        """加载所有知识文档并分块"""
        docs = []
        for fpath in KNOWLEDGE_DIR.glob("*.md"):
            with open(fpath, "r", encoding="utf-8") as f:
                text = f.read()
            chunks = _split_text(text)
            docs.extend([
                {"content": chunk, "source": fpath.stem}
                for chunk in chunks
            ])
        return docs

    def build(self, force: bool = False):
        """构建/重建向量索引"""
        collection = self._get_collection()

        if not force and collection.count() > 0:
            print(f"已加载现有知识库，共 {collection.count()} 条")
            return

        docs = self.load_documents()
        if not docs:
            print("⚠ 未找到知识文档")
            return

        # 批量 embedding
        model = self._get_model()
        texts = [d["content"] for d in docs]
        metadatas = [{"source": d["source"]} for d in docs]
        ids = [f"doc_{i}" for i in range(len(texts))]

        # 清除旧数据
        if collection.count() > 0:
            collection.delete(ids=collection.get()["ids"])

        # 分批 embedding（避免内存溢出）
        batch_size = 32
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_meta = metadatas[i:i + batch_size]
            batch_ids = ids[i:i + batch_size]
            embeddings = model.encode(batch_texts, normalize_embeddings=True).tolist()
            collection.add(
                embeddings=embeddings,
                documents=batch_texts,
                metadatas=batch_meta,
                ids=batch_ids,
            )

        print(f"知识库构建完成，共 {len(texts)} 条记录")

    def search(self, query: str, k: int = 5) -> list[dict]:
        """检索相关知识"""
        collection = self._get_collection()
        if collection.count() == 0:
            self.build()

        model = self._get_model()
        query_embedding = model.encode([query], normalize_embeddings=True).tolist()

        results = collection.query(
            query_embeddings=query_embedding,
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )

        return [
            {
                "content": results["documents"][0][i],
                "source": results["metadatas"][0][i].get("source", "unknown"),
                "score": round(1 - results["distances"][0][i] / 2, 4),
            }
            for i in range(len(results["documents"][0]))
        ]


# ====== 全局单例 ======

_kb_instance: KnowledgeBase | None = None


def get_knowledge_base() -> KnowledgeBase:
    global _kb_instance
    if _kb_instance is None:
        _kb_instance = KnowledgeBase()
        _kb_instance.build()
    return _kb_instance
