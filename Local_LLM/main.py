from llama_cpp import Llama
import time
import gc
import os

from text_dictifier import PdfReader, pdf_to_dict
from yaml_parser import Path, build_prompt_blocks

mopa = lambda name: str(Path("Models") / name)

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
                     f"Bewertende KI: {name.replace(".gguf", "")} \n\n")

        """
        Mit NVIDIA RTX 3050 6GB VRAM:
        - gpt-oss-20b-Q2_K => n_gpu_layers=17
        - Qwen3.5-4B-Q4_K_M => n_gpu_layers=-1 (Seitenzahl = ca. 10)
        - Qwen3.5-4B-BF16 => n_gpu_layers=-1 (Seitenzahl = ca. 10)
        - Qwen3.5-9B-Q6_K
        - Qwen3.5-9B-Q8_0
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

def directory_orderer(dir_name="Models",
                      phrase = "Which models would you like to run? (Hint: They will run in the given order.)",
                      as_dir=False):

    file_list = os.listdir(Path(dir_name))

    sum_str: str = ""
    for (index, file) in enumerate(file_list):
        sum_str += f"{index + 1}. {file.replace(".gguf", "").replace(".pdf", "")}; "

    models_to_run = input(f"{phrase}\n"
                          f"Available options: {sum_str[:-2]} \n"
                          f"Pick by number (comma-separated for multiple, e.g. 1,3): ")

    if as_dir:
        return [Path("Papers") / (file_list[int(index) - 1]) for index in models_to_run.split(",")]

    return [file_list[int(index) - 1] for index in models_to_run.split(",")]


with open("AI_conduct/Priming_MOD.txt", "r", encoding="utf-8") as priming_file:
    priming, instructions = priming_file.read().split("#### 1) System prompt")[1].split("#### 2) User prompt")

rse_definition, categories_block, category_guidance_block = build_prompt_blocks("AI_conduct/Ground_Truth_MOD.txt")

answer = input("Should all available publications be analyzed (Y)\nor only one specific publication (n): ").lower()
if answer in ['', 'y']:
    answer = input("Should the publications be analyzed in a specific order (y) \nor in random order (N): ").lower()
    if answer == 'y':
        path_list = directory_orderer("Papers",
                                      "Please provide the order in which the publications should be analyzed.",
                                      True)

    elif answer in ['n', '']:
        directory = Path("Papers")
        path_list = directory.iterdir()

    else:
        raise "Invalid response!!!"

elif answer == 'n':
    paper_name = input("Please provide the name of the publication: ")
    path_list = [Path("Papers") / (paper_name + ".pdf")]
else:
    raise "Invalid response!!!"

# Model path options: 1. "Qwen3.5-9B-Q8_0"  (Fantastic speed, high accuracy and high robustness much better than standard online LLM)
#                     2. "Qwen3.5-4B-BF16"  (Fantastic speed, high accuracy and high robustness better than standard online LLM)

model_list = directory_orderer()
for mod in model_list:
    for path in path_list:
        analyzer(path, mod)
        time.sleep(3)
