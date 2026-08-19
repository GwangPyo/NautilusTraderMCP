import dspy
import json
from pathlib import Path
from rags.load_dspy import load_embedder
from typing import Container, Tuple
from dspy.retrievers import Retrieve
from pathlib import Path
 
class Builder:

    DOCS_DIR = Path(__file__).parent.parent / "docs"
    TEXT_SUFFIXES = {".md", ".py", ".rs", ".css"}
    CHUNK_SIZE = 2000
    CHUNK_OVERLAP = 200

    def __init__(self, 
                 dir: str | None = None, 
                 suffix: Container[str] | None = None, 
                 ):
        
        if dir is None: 
            dir = self.DOCS_DIR
        if suffix is None: 
            suffix = self.TEXT_SUFFIXES

        self.dir = dir 
        self.suffix=  suffix
        # recursive read the text 
        self.cursor = map(lambda x: (x, x.read_text()), 
                          filter(lambda x: x.suffix in self.suffix,  
                                 self.dir.rglob("*")))
        self.cursor = self.cursor_to_dict()
        self.folders = filter(lambda x: x.is_dir(), self.dir.rglob("*"))
        self.embedder = load_embedder(model_name ='gemini-embedding-2', caching = False)

    
    @classmethod
    def chunk_text(cls, text: str) -> list[str]:
        step = cls.CHUNK_SIZE - cls.CHUNK_OVERLAP
        return [text[i:i + cls.CHUNK_SIZE] for i in range(0, len(text), step)] or [""]

    def cursor_to_dict(self) -> dict:
        tree: dict = {}
        for path, content in self.cursor:
            *dirs, name = path.relative_to(self.dir).parts
            node = tree
            for part in dirs:
                node = node.setdefault(part, {})
            node[name] = self.chunk_text(content)
        return tree

    def __call__(self, output_path: Path | str) -> None:
        text_list, shape = self.unfold(self.cursor, [])
        # dspy.retrievers.Embeddings가 자체적으로 배치 임베딩 + 인덱스 저장까지 다 함
        retriever = dspy.retrievers.Embeddings(corpus=text_list, embedder=self.embedder)
        retriever.save(str(output_path))
        (Path(output_path) / "shape.json").write_text(json.dumps(shape))


    # folder 구조를 보존하기 위한 helper. 
    @staticmethod
    def unfold(x: dict[str, dict[str] | str], container: list) -> Tuple[list, dict]:
        shape = {}
        for k, v in x.items():
            if isinstance(v, dict):
                _, shape[k] = Builder.unfold(v, container)
            elif isinstance(v, list):
                container.extend(v)  # chunk 리스트 -> shape엔 chunk 개수만 기록
                shape[k] = len(v)
            else:
                container.append(v)
                shape[k] = None
        return container, shape

    @staticmethod
    def fold(flatten_list: list, shape_dict: dict) -> dict[str, dict[str]]:
        it = iter(flatten_list)

        def _fold(shape):
            result = {}
            for k, v in shape.items():
                if isinstance(v, dict):
                    result[k] = _fold(v)
                elif isinstance(v, int): 
                    result[k] = [next(it) for _ in range(v)]
                else:
                    result[k] = next(it)
            return result

        return _fold(shape_dict)



if __name__ == '__main__':
    builder = Builder()
    builder(Path(__file__).parent / "rags")
