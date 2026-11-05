"""Builds notebooks/finetune_marker.ipynb (run: python notebooks/make_finetune_notebook.py).

Phase 4 of the experiment plan: LoRA fine-tuning of Qwen3-4B (the best open model of Phase 3) on the marking
data from eval/phase4.py data, then a server for the adapters with the same API, link and key as the other Colab
notebooks, plus /v1/adapter (switch adapter) and /v1/training_log, so Claude can test every adapter from the laptop.
Plain transformers + PEFT (QLoRA on the same 4-bit model as Phase 3): no Unsloth, fewer version problems on Colab.
Kept as a script so the notebook stays valid JSON.
"""
import json
from pathlib import Path

md = lambda s: {"cell_type": "markdown", "metadata": {}, "source": s.strip("\n").splitlines(keepends=True)}  # noqa: E731
code = lambda s: {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],  # noqa: E731
                  "source": s.strip("\n").splitlines(keepends=True)}

cells = [
    md("""
# Fine-tuning Qwen3-4B to mark KAFA answers (Google Colab + ngrok)

Experiment plan v3, **Phase 4**. Qwen3-4B was the best open model in Phase 3. This notebook teaches it to mark like
the best marker (GPT-6 Luna), using the silver training answers (never the teacher answers), with **LoRA**: small
extra weights on top of the same 4-bit model as Phase 3 and the laptop.

The supervisor's small grid: **LoRA rank 8 vs 16** and **1 vs 2 epochs** (learning rate 2e-4). Each rank is trained
for 2 epochs and saved after each epoch, so 2 training runs give 4 adapters: `r8e1`, `r8e2`, `r16e1`, `r16e2`.

**Before you start**
1. **Runtime → Change runtime type → L4 GPU** (the same GPU as Phase 3).
2. The ngrok secret `NGROK_AUTHTOKEN` is already in Colab Secrets (from the other notebooks).
3. On the laptop, the file `data/finetune/kafa_marker_sft.jsonl` (made by Claude) is ready to upload.

**Then:** Runtime → **Run all**.
- Cell 4 shows a **Choose files** button: pick `kafa_marker_sft.jsonl` from the project folder.
- Cell 5 trains (about **60–90 minutes**; the progress bar shows the time left). Keep the tab open.
- Cell 6 downloads `kafa_marker_adapters.zip` to your laptop: keep it (it is the fine-tuned model).
- Cell 8 prints the **LINK** and **KEY**: paste them in the website (**📊 Penilaian → Qwen on Colab**) and tell
  Claude. Claude then tests every adapter (about 15–20 minutes each). Run cell 10 to keep the session alive.

**If Colab disconnects after training:** Run all again and, at cell 4, choose **both** `kafa_marker_sft.jsonl` and
`kafa_marker_adapters.zip`: training is then skipped.

When Claude says the tests are done: run the last cell, then **Runtime → Disconnect and delete runtime**.
"""),
    md("## 1. Check the GPU"),
    code("""
!nvidia-smi --query-gpu=name,memory.total --format=csv || echo "No GPU: Runtime -> Change runtime type -> L4 GPU"
"""),
    md("## 2. Install packages (the same transformers version as the Phase 3 server)"),
    code("""
!pip -q install "transformers==4.55.4" "peft==0.17.1" "accelerate>=1.8" "bitsandbytes>=0.45" fastapi "uvicorn[standard]" pyngrok
"""),
    md("## 3. Settings"),
    code("""
import secrets

BASE_ID = "unsloth/Qwen3-4B-Instruct-2507-bnb-4bit"   # the same 4-bit Qwen as the laptop and Phase 3
SERVED = "kafa/qwen3-4b-marker"                      # the tests see kafa/qwen3-4b-marker-r8e1, ...
RANKS = [8, 16]          # LoRA rank
EPOCHS = 2               # an adapter is kept after every epoch
LR = 2e-4                # learning rate (constant after 5 warm-up steps, so the epoch-1 adapter equals a 1-epoch run)
BATCH, ACCUM = 1, 8      # 8 answers per update
MAX_LEN = 4096           # tokens; longer examples are left out
PORT = 8000

try:
    from google.colab import userdata
    NGROK_AUTHTOKEN = userdata.get("NGROK_AUTHTOKEN")
except Exception:
    NGROK_AUTHTOKEN = None
if not NGROK_AUTHTOKEN:
    from getpass import getpass
    NGROK_AUTHTOKEN = getpass("Paste your ngrok authtoken: ").strip()

API_KEY = secrets.token_urlsafe(24)   # the website must send it, so strangers who find the link cannot use your GPU
print("Settings ready. Base model:", BASE_ID)
"""),
    md("""
## 4. Upload the training data

Click **Choose files** and pick `data/finetune/kafa_marker_sft.jsonl` from the project folder
(after a disconnect: also `kafa_marker_adapters.zip`).
"""),
    code("""
import json, os, zipfile
from google.colab import files

DATA = "kafa_marker_sft.jsonl"
if not os.path.exists(DATA):
    for name in files.upload():
        if name.endswith(".zip"):
            zipfile.ZipFile(name).extractall("/content/adapters")
            print("Adapters restored from", name)
        elif name.endswith(".jsonl") and name != DATA:
            os.rename(name, DATA)
rows = [json.loads(line) for line in open(DATA, encoding="utf-8")]
train = [r for r in rows if r["split"] == "train"]
val = [r for r in rows if r["split"] == "val"]
print(f"{len(train)} training and {len(val)} validation examples")
"""),
    md("""
## 5. Train the LoRA adapters (about 60–90 minutes)

QLoRA: the 4-bit base model stays frozen; only the small LoRA weights learn. The model sees exactly the request the
marking system sends (system rules + question, rubric, reference answer, textbook text, pupil answer) and learns
only the reply (the JSON marking and feedback). After each epoch the validation loss (on answers to other questions)
is measured and the adapter is saved.
"""),
    code("""
import gc, glob, shutil, time
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
import torch
torch._dynamo.config.disable = True      # no torch.compile: it recompiles for every prompt length
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments, set_seed

tokenizer = AutoTokenizer.from_pretrained(BASE_ID)
if tokenizer.pad_token_id is None:
    tokenizer.pad_token_id = tokenizer.eos_token_id
END = "<|im_end|>"


def encode(row):
    \"\"\"The prompt exactly as the server builds it; the loss is only on the reply and its end token.\"\"\"
    prompt = tokenizer.apply_chat_template(row["messages"][:2], add_generation_prompt=True, tokenize=False)
    p = tokenizer(prompt, add_special_tokens=False)["input_ids"]
    a = tokenizer(row["messages"][2]["content"] + END, add_special_tokens=False)["input_ids"]
    return {"input_ids": p + a, "labels": [-100] * len(p) + a}


def encoded(rows):
    out = [encode(r) for r in rows]
    return [x for x in out if len(x["input_ids"]) <= MAX_LEN], sum(len(x["input_ids"]) > MAX_LEN for x in out)


train_set, cut = encoded(train)
val_set, _ = encoded(val)
tokens = sum(len(x["input_ids"]) for x in train_set)
print(f"{len(train_set)} training examples, {tokens / len(train_set):.0f} tokens each on average "
      f"({cut} too long, left out); {len(val_set)} validation examples")


def collate(batch):
    n = max(len(b["input_ids"]) for b in batch)
    pad = lambda rows, v: [r + [v] * (n - len(r)) for r in rows]  # noqa: E731
    return {"input_ids": torch.tensor(pad([b["input_ids"] for b in batch], tokenizer.pad_token_id)),
            "attention_mask": torch.tensor(pad([[1] * len(b["input_ids"]) for b in batch], 0)),
            "labels": torch.tensor(pad([b["labels"] for b in batch], -100))}


ADAPTERS = "/content/adapters"
LOG_PATH = f"{ADAPTERS}/training_log.json"
os.makedirs(ADAPTERS, exist_ok=True)
TRAIN_LOG = json.load(open(LOG_PATH)) if os.path.exists(LOG_PATH) else {
    "base": BASE_ID, "learning_rate": LR, "schedule": "constant, 5 warm-up steps", "epochs": EPOCHS,
    "answers_per_update": BATCH * ACCUM, "lora": "alpha = 2 x rank, dropout 0.05, all attention and MLP projections",
    "train_examples": len(train_set), "val_examples": len(val_set), "train_tokens": tokens, "runs": {}, "adapters": {}}


def train_rank(rank):
    set_seed(7)
    model = AutoModelForCausalLM.from_pretrained(BASE_ID, device_map={"": 0}, torch_dtype=torch.bfloat16)
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True,
                                            gradient_checkpointing_kwargs={"use_reentrant": False})
    model = get_peft_model(model, LoraConfig(
        r=rank, lora_alpha=2 * rank, lora_dropout=0.05, bias="none", task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]))
    out = f"/content/runs/r{rank}"
    args = TrainingArguments(
        output_dir=out, num_train_epochs=EPOCHS, learning_rate=LR, lr_scheduler_type="constant_with_warmup",
        warmup_steps=5, per_device_train_batch_size=BATCH, gradient_accumulation_steps=ACCUM,
        per_device_eval_batch_size=1, eval_strategy="epoch", save_strategy="epoch", logging_steps=5,
        prediction_loss_only=True, label_names=["labels"], bf16=True, gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False}, optim="adamw_torch",
        remove_unused_columns=False, report_to="none", seed=7)
    trainer = Trainer(model=model, args=args, train_dataset=train_set, eval_dataset=val_set, data_collator=collate)
    t0 = time.time()
    trainer.train()
    hist = trainer.state.log_history
    evals = [h for h in hist if "eval_loss" in h]
    ckpts = sorted(glob.glob(f"{out}/checkpoint-*"), key=lambda p: int(p.rsplit("-", 1)[1]))
    for e, (ck, ev) in enumerate(zip(ckpts, evals), 1):
        dst = f"{ADAPTERS}/r{rank}e{e}"
        os.makedirs(dst, exist_ok=True)
        for f in ("adapter_config.json", "adapter_model.safetensors"):
            shutil.copy(f"{ck}/{f}", dst)
        TRAIN_LOG["adapters"][f"r{rank}e{e}"] = {"rank": rank, "epoch": e, "eval_loss": round(ev["eval_loss"], 4)}
    TRAIN_LOG["runs"][f"r{rank}"] = {
        "minutes": round((time.time() - t0) / 60, 1),
        "train_loss": [[round(h["epoch"], 2), round(h["loss"], 4)] for h in hist if "loss" in h],
        "eval_loss": [[round(h["epoch"], 2), round(h["eval_loss"], 4)] for h in evals]}
    json.dump(TRAIN_LOG, open(LOG_PATH, "w"), indent=1)
    print(f"r{rank}: {TRAIN_LOG['runs'][f'r{rank}']['minutes']} minutes; validation loss after each epoch:",
          [x[1] for x in TRAIN_LOG["runs"][f"r{rank}"]["eval_loss"]])
    del trainer, model
    gc.collect()
    torch.cuda.empty_cache()
    shutil.rmtree(out, ignore_errors=True)


for rank in RANKS:
    if all(f"r{rank}e{e}" in TRAIN_LOG["adapters"] for e in range(1, EPOCHS + 1)):
        print(f"r{rank}: already trained, skipped")
    else:
        train_rank(rank)
print("Validation loss per adapter (lower is better):", {k: v["eval_loss"] for k, v in TRAIN_LOG["adapters"].items()})
"""),
    md("## 6. Keep the adapters: `kafa_marker_adapters.zip` is downloaded to your laptop"),
    code("""
shutil.make_archive("/content/kafa_marker_adapters", "zip", ADAPTERS)
files.download("/content/kafa_marker_adapters.zip")
print("Downloading kafa_marker_adapters.zip: keep it (the fine-tuned model, about",
      round(os.path.getsize("/content/kafa_marker_adapters.zip") / 1e6), "MB)")
"""),
    md("""
## 7. Load the adapters and start the server

The base model is loaded as in Phase 3 (4-bit, float16) with all adapters on top. The tests switch adapters through
`POST /v1/adapter` (`base` = no adapter). The same OpenAI-style API as the other notebooks; every request needs the
header `Authorization: Bearer <KEY>`.
"""),
    code("""
import threading, traceback, uuid
import uvicorn
from fastapi import FastAPI, Header, HTTPException
from peft import PeftModel
from pydantic import BaseModel

if "model" in globals():
    del model
gc.collect()
torch.cuda.empty_cache()
NAMES = sorted(TRAIN_LOG["adapters"], key=lambda a: TRAIN_LOG["adapters"][a]["eval_loss"])   # best first
model = PeftModel.from_pretrained(
    AutoModelForCausalLM.from_pretrained(BASE_ID, device_map={"": 0}, torch_dtype=torch.float16),
    f"{ADAPTERS}/{NAMES[0]}", adapter_name=NAMES[0])
for n in NAMES[1:]:
    model.load_adapter(f"{ADAPTERS}/{n}", adapter_name=n)
model.eval()
ACTIVE = NAMES[0]
model.set_adapter(ACTIVE)
PRECISION = "4-bit NF4"
STOP = sorted({i for i in [tokenizer.eos_token_id, tokenizer.convert_tokens_to_ids(END)] if isinstance(i, int)})
torch.cuda.reset_peak_memory_stats()


def served_id():
    return BASE_ID if ACTIVE == "base" else f"{SERVED}-{ACTIVE}"


@torch.inference_mode()
def generate(messages, max_tokens=900, temperature=0.0):
    inputs = tokenizer.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt",
                                           return_dict=True).to(model.device)
    kw = dict(max_new_tokens=max_tokens, pad_token_id=tokenizer.pad_token_id, eos_token_id=STOP, disable_compile=True)
    if temperature and temperature > 0:
        kw.update(do_sample=True, temperature=temperature, top_p=0.9)
    else:
        kw.update(do_sample=False, temperature=None, top_p=None, top_k=None)   # greedy = repeatable marking
    try:
        if ACTIVE == "base":
            with model.disable_adapter():
                out = model.generate(**inputs, **kw)
        else:
            out = model.generate(**inputs, **kw)
        n_in = inputs["input_ids"].shape[1]
        new = out[0, n_in:]
        return tokenizer.decode(new, skip_special_tokens=True).strip(), n_in, len(new)
    finally:
        del inputs
        gc.collect()
        torch.cuda.empty_cache()


app = FastAPI(title="Fine-tuned Qwen3-4B for KAFA UPKK")
gpu_lock = threading.Lock()


class ChatRequest(BaseModel):
    messages: list[dict]
    max_tokens: int = 900
    temperature: float = 0.0
    model: str | None = None


class AdapterRequest(BaseModel):
    name: str


def check_key(authorization):
    if authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="wrong or missing key")


@app.get("/health")
def health(authorization: str | None = Header(default=None)):
    check_key(authorization)
    return {"status": "ok", "model": served_id(), "precision": PRECISION, "gpu": torch.cuda.get_device_name(0),
            "gpu_memory_gb": round(torch.cuda.max_memory_allocated() / 1e9, 1), "adapter": ACTIVE,
            "adapters": NAMES + ["base"]}


@app.post("/v1/adapter")
def set_adapter(req: AdapterRequest, authorization: str | None = Header(default=None)):
    global ACTIVE
    check_key(authorization)
    if req.name not in NAMES + ["base"]:
        raise HTTPException(status_code=404, detail=f"unknown adapter {req.name}; choose from {NAMES + ['base']}")
    with gpu_lock:
        if req.name != "base":
            model.set_adapter(req.name)
        ACTIVE = req.name
    print(time.strftime("%H:%M"), "adapter now", ACTIVE)
    return health(authorization)


@app.get("/v1/training_log")
def training_log(authorization: str | None = Header(default=None)):
    check_key(authorization)
    return TRAIN_LOG


@app.post("/v1/chat/completions")
def chat_completions(req: ChatRequest, authorization: str | None = Header(default=None)):
    check_key(authorization)
    max_tokens = max(1, min(req.max_tokens, 2048))
    with gpu_lock:
        t0 = time.time()
        try:
            text, n_in, n_out = generate(req.messages, max_tokens, req.temperature)
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}"[:300])
    return {"id": f"chatcmpl-{uuid.uuid4().hex[:12]}", "object": "chat.completion", "model": served_id(),
            "choices": [{"index": 0, "message": {"role": "assistant", "content": text},
                         "finish_reason": "length" if n_out >= max_tokens else "stop"}],
            "usage": {"prompt_tokens": n_in, "completion_tokens": n_out, "total_tokens": n_in + n_out},
            "latency_ms": int((time.time() - t0) * 1000)}


try:                                          # cell run again: stop the old server so the port is free
    server.should_exit = True
    time.sleep(3)
except NameError:
    pass
server = uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=PORT, log_level="warning"))
threading.Thread(target=server.run, daemon=True).start()
time.sleep(3)
print("Server running on port", PORT, "with adapters", NAMES, "(active:", ACTIVE + ")")
"""),
    md("## 8. Open the ngrok link → copy LINK and KEY into the website"),
    code("""
from pyngrok import ngrok

ngrok.set_auth_token(NGROK_AUTHTOKEN)
ngrok.kill()                                  # close an old tunnel if this cell is run again
# A free ngrok account has ONE link. If an older Colab session still holds it (ERR_NGROK_334), ngrok frees it
# about a minute after that session stops: wait and try again for up to 5 minutes.
PUBLIC_URL = None
for attempt in range(10):
    try:
        PUBLIC_URL = ngrok.connect(PORT, "http").public_url
        break
    except Exception as e:                    # pyngrok's error class moved between versions: match the ngrok code instead
        if "ERR_NGROK_334" not in str(e):
            raise
        ngrok.kill()
        print(f"The ngrok link is still used by an older session; trying again in 30 s ({attempt + 1}/10)...")
        time.sleep(30)
if PUBLIC_URL is None:
    raise SystemExit("The ngrok link is still busy. Stop the old session: Runtime -> Manage sessions -> Terminate "
                     "every other session (or https://dashboard.ngrok.com/agents -> stop the agent), then run this cell again.")

print("=" * 72)
print(f"Fine-tuned Qwen3-4B ({PRECISION}, {torch.cuda.get_device_name(0)}), adapters {NAMES}")
print("Paste these on the website:  📊 Penilaian -> Qwen on Colab")
print()
print("  LINK :", PUBLIC_URL)
print("  KEY  :", API_KEY)
print("=" * 72)
"""),
    md("## 9. Self-test: one validation answer marked through the public link"),
    code("""
import requests

h = {"Authorization": f"Bearer {API_KEY}", "ngrok-skip-browser-warning": "true"}
for _ in range(6):   # a new ngrok link can show its own error page for a few seconds
    r = requests.get(f"{PUBLIC_URL}/health", headers=h, timeout=30)
    if r.ok and r.headers.get("content-type", "").startswith("application/json"):
        print(r.json())
        break
    print(f"Link not ready yet (HTTP {r.status_code}); trying again in 10 s...")
    time.sleep(10)
else:
    print("The link still does not reach the server: run cells 7 and 8 again. Reply was:", r.text[:300])
ex = val[0]
r = requests.post(f"{PUBLIC_URL}/v1/chat/completions", headers=h, timeout=300,
                  json={"messages": ex["messages"][:2], "max_tokens": 900})
if r.ok:
    reply = r.json()["choices"][0]["message"]["content"]
    print("Reply:", reply[:600])
    try:
        got = [c["verdict"] for c in json.loads(reply)["criteria"]]
        print("Valid JSON. Verdicts:", got, "| expected:", [c["verdict"] for c in json.loads(ex["messages"][2]["content"])["criteria"]])
    except Exception as e:
        print("Not valid marking JSON:", e)
else:
    print(f"FAILED (HTTP {r.status_code}): {r.text[:500]}")   # copy this to Claude
"""),
    md("""
## 10. Keep it running

Leave this tab open while Claude tests the adapters (about 15–20 minutes each) and do not let the laptop sleep.
This cell keeps the session busy so Colab does not stop it for being idle (stop it with ■ when you are done).
"""),
    code("""
try:
    while True:
        time.sleep(60)
        print(time.strftime("%H:%M"), "server alive:", PUBLIC_URL, "adapter:", ACTIVE)
except KeyboardInterrupt:
    print("stopped keeping alive (the server is still running)")
"""),
    code("""
# Shut down: close the public link and the server
ngrok.kill()
server.should_exit = True
print("Stopped. In the website, remove the link (Qwen on Colab -> Remove).")
"""),
]

nb = {"cells": cells, "metadata": {"accelerator": "GPU", "colab": {"provenance": [], "gpuType": "L4"},
                                    "kernelspec": {"display_name": "Python 3", "name": "python3"},
                                    "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 0}
out = Path(__file__).with_name("finetune_marker.ipynb")
out.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
print("wrote", out)
