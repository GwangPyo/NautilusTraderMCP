import dspy
import json
from pathlib import Path
from rags.load_dspy import load_embedder
from rags.rag_build import Builder


class RAGSearch:
    def __init__(self,
                 data_path = './rags',
                 model_name:str='gemini-embedding-2',
                 caching=True):
        self.embedding = load_embedder(model_name=model_name, caching=caching)
        self.retriever = dspy.retrievers.Embeddings.from_saved(str(data_path), embedder=self.embedding)
        self.shape = json.loads((Path(data_path) / "shape.json").read_text())

    def show_keys(self) -> dict:
        return self.shape

    def __call__(self, search_keywords: str, *, keys: list[str] | None = None, top_k: int = 20):
        """Find passages (chunks) in the nautilus_trader docs (ragged_docs) that are
        semantically close to search_keywords.

        Call show_keys() first to see the folder/file structure.

        :param search_keywords: natural-language search query.
        :param keys: narrow the search to a subfolder by listing show_keys()'s nested
            dict keys top-down, e.g. ['concepts', 'strategies.md']. Omit (None) to
            search the whole doc set.
        :param top_k: number of results to return.
        :return: list of (corpus index, matched text chunk), most similar first.
        """
        if not keys:
            self.retriever.k = top_k
            result = self.retriever(search_keywords)
            return list(zip(result.indices, result.passages))

        # keys로 지정된 서브트리에 속하는 corpus 인덱스만 추려서 그 안에서 다시 검색
        index_tree = Builder.fold(list(range(len(self.retriever.corpus))), self.shape)
        target = index_tree
        for k in keys:
            target = target[k]
        idxs, _ = Builder.unfold(target, [])

        sub_corpus = [self.retriever.corpus[i] for i in idxs]
        sub_retriever = dspy.retrievers.Embeddings(corpus=sub_corpus, embedder=self.embedding, k=top_k)
        result = sub_retriever(search_keywords)
        return [(idxs[i], passage) for i, passage in zip(result.indices, result.passages)]



if __name__ == '__main__':
    print(RAGSearch()('what is a strategy', keys=['concepts', ]))


    


    
