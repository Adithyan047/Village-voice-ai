import os
import glob
import re
from typing import List, Dict, Any

class RAGStore:
    def __init__(self, knowledge_dir: str = None):
        if knowledge_dir is None:
            # Look for data/knowledge up the directory tree
            base = os.path.dirname(__file__)
            for _ in range(4):
                candidate = os.path.join(base, "data", "knowledge")
                if os.path.exists(candidate):
                    knowledge_dir = candidate
                    break
                base = os.path.dirname(base)
            if not knowledge_dir:
                knowledge_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "knowledge")
        self.knowledge_dir = os.path.abspath(knowledge_dir)
        self.documents = []
        self.reload_documents()

    def reload_documents(self):
        self.documents = []
        files = glob.glob(os.path.join(self.knowledge_dir, "*.md"))
        for filepath in sorted(files):
            filename = os.path.basename(filepath)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Extract title from first line #
            lines = content.splitlines()
            title = lines[0].replace("#", "").strip() if lines else filename

            # Break into sections/chunks
            sections = content.split("## ")
            for sec in sections:
                if not sec.strip():
                    continue
                sec_lines = sec.splitlines()
                sec_title = sec_lines[0].strip() if sec_lines else "General"
                chunk_text = "\n".join(sec_lines[1:]).strip()
                
                self.documents.append({
                    "doc": filename,
                    "title": title,
                    "section": sec_title,
                    "content": sec,
                    "chunk": chunk_text
                })

    def search(self, query: str, category: str = "", top_k: int = 3) -> List[Dict[str, str]]:
        query_words = set(re.findall(r'\w+', query.lower()))
        category_words = set(re.findall(r'\w+', category.lower()))
        
        scored_docs = []
        for doc in self.documents:
            doc_text = (doc["doc"] + " " + doc["title"] + " " + doc["section"] + " " + doc["content"]).lower()
            text_words = set(re.findall(r'\w+', doc_text))
            
            title_words = set(re.findall(r'\w+', (doc["doc"] + " " + doc["title"]).lower()))
            overlap = len(query_words.intersection(text_words))
            title_overlap = len(query_words.intersection(title_words)) * 5
            cat_overlap = len(category_words.intersection(title_words)) * 3
            score = overlap + title_overlap + cat_overlap

            if score > 0:
                # Format snippet citation
                snippet = doc["chunk"][:180].replace("\n", " ") + "..." if len(doc["chunk"]) > 180 else doc["chunk"].replace("\n", " ")
                citation = f"{doc['section']}: {snippet}"
                scored_docs.append({
                    "doc": doc["doc"],
                    "title": doc["title"],
                    "citation": citation,
                    "score": score
                })
        
        # Sort by score descending
        scored_docs.sort(key=lambda x: x["score"], reverse=True)
        
        results = []
        seen = set()
        for d in scored_docs:
            key = f"{d['doc']}-{d['title']}"
            if key not in seen:
                seen.add(key)
                results.append({
                    "doc": d["doc"],
                    "title": d["title"],
                    "citation": d["citation"]
                })
            if len(results) >= top_k:
                break
                
        # Default fallback citation if no match found
        if not results:
            results.append({
                "doc": "06_civic_severity_matrix.md",
                "title": "Comprehensive Civic Issue Severity Matrix",
                "citation": "Standard rural civic issue classification guidelines applied."
            })
            
        return results

rag_store = RAGStore()
