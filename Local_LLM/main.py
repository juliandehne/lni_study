from llama_cpp import Llama
import time
import gc

from text_dictifier import PdfReader, pdf_to_dict
from yaml_parser import Path, build_prompt_blocks

mopa = lambda name: str(Path("Models") / (name + ".gguf"))

class Model:
    def __init__(self,
                 model_name,
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

        # Model initialization
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

        self.LLM = Llama(model_path=mopa(model_name),
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


def context(prompt, model_name, tolerance=2000):
    tokenizer_model = Llama(
        model_path=mopa(model_name),
        verbose=False
    )

    try:
        return len(
            tokenizer_model.tokenize(
                prompt.encode("utf-8"),
                add_bos=True,
                special=True
            )
        ) + tolerance

    finally:
        tokenizer_model.close()


# Model path options: 1. "Qwen3.5-4B-BF16"                        (medium speed, high accuracy and high robustness)
#                     2. "Qwen3.5-4B-Q4_K_M"                      (high speed, medium accuracy and high robustness)
#                     3. "gpt-oss-20b-Q2_K"                       (high accuracy)
#                     4. "gpt-oss-20b-F16"                        (Not robust)
#                     5. "qwen3.5-8b-distilled-Q8_0-MID"

def analyzer(paper_path, name = "Qwen3.5-4B-BF16"):
    with open("run_tracker.txt", "r", encoding="utf-8") as run_tracker_file:
        run = int(run_tracker_file.read())

    paper = pdf_to_dict(paper_path)
    prompt = instructions.format(
        row=paper,
        rse_definition=rse_definition,
        categories_block=categories_block,
        category_guidance_block=category_guidance_block
    )

    with open("run_tracker.txt", "w", encoding="utf-8") as tracker_file:
        tracker_file.write(str(run + 1))

    with open(f"Reports/report_{run}.txt", "w", encoding="utf-8") as report:
        report.write(f"Name der Publikation: {paper_path.stem} \n"
                     f"Bewertende KI: {name} \n\n")

        """
        Mit NVIDIA RTX 3050 6GB VRAM:
        - gpt-oss-20b-Q2_K => n_gpu_layers=17
        - Qwen3.5-4B-Q4_K_M => n_gpu_layers=-1 (Seitenzahl = ca. 10)
        - Qwen3.5-4B-BF16.gguf => n_gpu_layers=-1 (Seitenzahl = ca. 10)
        """

        model = Model(model_name=name, n_ctx=context(prompt, name), priming=priming)

        """ prediction and timing """
        start_time = time.time()
        prediction = model.predict(prompt)
        sek = time.time() - start_time
        min_ = sek // 60

        report.write(f"Anzahl bewerteter Seiten: {len(PdfReader(paper_path).pages)} \n"
                     f"Zeitaufwand: {int(min_)} Minuten und {int(sek - 60 * min_)} Sekunden \n"
                     f"KI Bewertung: {prediction} \n")

        report.flush()

    model.LLM.close()
    del model
    gc.collect()


with open("AI_conduct/Priming_MOD.txt", "r", encoding="utf-8") as priming_file:
    priming, instructions = priming_file.read().split("#### 1) System prompt")[1].split("#### 2) User prompt")

rse_definition, categories_block, category_guidance_block = build_prompt_blocks("AI_conduct/Ground_Truth_MOD.txt")

answer = input("Sollen alle Publikationen bewertet werden (Y)\noder nur eine bestimmte Publikation (n): ").lower()
if answer in ['', 'y']:
    directory = Path("Papers")
    for publication in directory.iterdir():
        analyzer(publication)

elif answer == 'n':
    paper_name = input("Geben Sie bitte den Namen der zu bewertenden Publikation an: ")
    analyzer(Path("Papers") / (paper_name + ".pdf"))

else:
    raise "Invalid response!!!"
