from llama_cpp import Llama
from pathlib import Path


def mopa_conv(model_path):
    model_path = Path("Models") / model_path.lstrip(r"\/")
    if not model_path.exists():
        raise FileNotFoundError(model_path)
    return str(model_path)

class Model:

    def __init__(self,
                 model_path,
                 n_ctx=2048,
                 n_gpu_layers=-1,
                 RANDOMSEED=42,
                 priming=None,

                 temp=0.7,
                 top_p=0.8,
                 top_k=50,
                 repeat_penalty=1.1,
                 max_tokens=2000,
                 stop=None,
                 seed=43):

        # Model initialisation
        self.priming = [
            {
                "role": "system",
                "content": "You are an assistant. Formulate the solution in pure text."
                if priming is None else priming
            }
        ]

        # Model prediction
        self.temp = temp
        self.top_p = top_p
        self.top_k = top_k
        self.repeat_penalty = repeat_penalty
        self.max_tokens = max_tokens
        self.stop = ["</s>"] if stop is None else stop
        self.seed = seed

        self.LLM = Llama(model_path=mopa_conv(model_path),
                         n_ctx=n_ctx,
                         n_gpu_layers=n_gpu_layers,
                         seed=RANDOMSEED,
                         swa_full=False,
                         verbose=False)

    def predict(self, problem: str):
        return self.LLM.create_chat_completion(
            messages=self.priming + [{"role": "user", "content": problem}],
            temperature=self.temp,
            top_p=self.top_p,
            top_k=self.top_k,
            repeat_penalty=self.repeat_penalty,
            max_tokens=self.max_tokens,
            stop=self.stop,
            seed=self.seed
        )["choices"][0]["message"]["content"].split("final<|message|>")[-1]

# Model path options: - r"\gpt-oss-20b-F16.gguf"
#                     - r"\Qwen3VL-8B-Instruct-Q4_K_M.gguf"
#                     - r"\DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf"
#                     - r"\gpt-oss-20b-Q2_K.gguf"
#                     - r"Qwen3.5-4B-Q4_K_M.gguf"

mopa = r"Qwen3.5-4B-Q4_K_M.gguf"
model = Model(model_path=mopa, n_ctx=2000, n_gpu_layers=-1)
prediction = model.predict("Two large and 1 small pumps can fill a swimming pool "
                         + "in 4 hours. One large and 3 small pumps can also fill "
                         + "the same swimming pool in 4 hours. How many hours will "
                         + "it take 4 large and 4 small pumps to fill the swimming "
                         + "pool? (We assume that all large pumps are similar and "
                         + "all small pumps are also similar.)")
print(prediction)
