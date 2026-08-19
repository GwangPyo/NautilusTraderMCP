import dspy 
from dspy.utils.callback import BaseCallback
import dotenv 
import os 
from typing import Literal


_KEY_NAMES = {"gpt": "OPENAI_API_KEY", "claude": "ANTHROPIC_API_KEY", "gemini": "GEMINI_API_KEY"}


def _require_key(name: str) -> str:
    dotenv.load_dotenv()
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is not set. Add it to .env (project root) or export it before running.")
    return value


def load_model(types: Literal['gpt', 'claude', 'gemini'],
               model_name: str,
               max_tokens: int | None = None,
               cache: bool = True,
               callbacks: list[BaseCallback] | None = None,
               ):
    prefixes = {"gpt": "openai", "claude": "anthropic", "gemini": "gemini"}
    api_key = _require_key(_KEY_NAMES[types])

    lm = dspy.LM(f"{prefixes[types]}/{model_name}", api_key=api_key,
                 max_tokens=max_tokens, cache=cache, callbacks=callbacks,
                 )
    dspy.configure(lm=lm)
    return lm


def load_embedder(model_name: str ='gemini-embedding-2',
            caching: bool = False
             ) ->dspy.Embedder:
    api_key = _require_key(_KEY_NAMES["gemini"])
    return dspy.Embedder(model=f"gemini/{model_name}", batch_size=100, caching=caching, api_key=api_key)


if __name__  == '__main__':
    load_model('gemini', 'gemini-3.7-flash')
    ans = dspy.Predict(dspy.Signature('question -> answer'))(question='What is the capital of France?').answer

    
    embedder = load_embedder(caching=True)
    print(embedder(ans))



