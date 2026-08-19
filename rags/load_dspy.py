import dspy 
from dspy.utils.callback import BaseCallback
import dotenv 
import os 
from typing import Literal


def load_model(types: Literal['gpt', 'claude', 'gemini'],
               model_name: str,
               max_tokens: int | None = None,
               cache: bool = True,
               callbacks: list[BaseCallback] | None = None,
               ):
    dotenv.load_dotenv()
    keys = {"gpt": os.environ['OPENAI_API_KEY'],
            "claude": os.environ['ANTHROPIC_API_KEY'],
            "gemini": os.environ['GEMINI_API_KEY']}
    prefixes = {"gpt": "openai", "claude": "anthropic", "gemini": "gemini"}

    lm = dspy.LM(f"{prefixes[types]}/{model_name}", api_key=keys[types], 
                 max_tokens=max_tokens, cache=cache, callbacks=callbacks,
                 )
    dspy.configure(lm=lm)
    return lm


def load_embedder(model_name: str ='gemini-embedding-2',
            caching: bool = False
             ) ->dspy.Embedder:
    dotenv.load_dotenv()
    return dspy.Embedder(model=f"gemini/{model_name}", batch_size=100, caching=caching,
                          api_key=os.environ['GEMINI_API_KEY'])


if __name__  == '__main__':
    load_model('gemini', 'gemini-3.7-flash')
    ans = dspy.Predict(dspy.Signature('question -> answer'))(question='What is the capital of France?').answer

    
    embedder = load_embedder(caching=True)
    print(embedder(ans))



