from llama_cpp import Llama
from pypdf import PdfReader
from pathlib import Path
import time


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


def kontext(prompt, model_path):
    model = Llama(model_path=mopa_conv(model_path), verbose=False)
    return len(model.tokenize(prompt.encode("utf-8"), add_bos=True, special=True))

# Model path options: - r"\gpt-oss-20b-F16.gguf"
#                     - r"\Qwen3VL-8B-Instruct-Q4_K_M.gguf"
#                     - r"\DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf"
#                     - r"\gpt-oss-20b-Q2_K.gguf"

mopa = r"\gpt-oss-20b-Q2_K.gguf"

with open("AI_conduct/priming.txt") as priming_file, \
        open("AI_conduct/ground_truth.txt") as ground_truth_file, \
        open("run_tracker.txt", "r") as run_tracker_file:
    priming = priming_file.read()
    ground_truth = ground_truth_file.read()
    run = int(run_tracker_file.read())

    run_tracker_file.close()
    with open("run_tracker.txt", "w") as tracker_file:
        tracker_file.write(str(run+1))

    paper = PdfReader("Papers/SBEED.pdf")

    with open(f"Reports/report_{run}.txt", "w", encoding="utf-8") as report:

        report.write(f"Verwendetes Model: {Path(mopa).stem}. \n\n")
        start_time = time.time()
        paper_text = ""

        for count in range(int(input("Bitte einen Startpunkt angeben: "))-1, len(paper.pages)):
            paper_text = "\n\n".join([paper.pages[index].extract_text() or "" for index in range(len(paper.pages))])

            start_time = time.time()
            prompt = f"Nutze: {ground_truth}. Um die Publikationen zu bewerten: {paper_text}."

            """
            Mit NVIDIA RTX 3050 6GB VRAM:
            - gpt-oss-20b-Q2_K => n_gpu_layers=17
            """

            model = Model(model_path=mopa, n_ctx=kontext(prompt, mopa)+2000, priming=priming, n_gpu_layers=17)
            prediction = model.predict(prompt)

            report.write(f"Anzahl bewerteter Seiten: {count + 1}. \n")
            report.write(f"KI Bewertung: {prediction} \n")
            sek = time.time() - start_time
            min_ = sek // 60
            report.write(f"Zeitverbrauch: {int(min_)} Minuten und {int(sek - 60*min_)} Sekunden. \n\n")
            report.flush()
