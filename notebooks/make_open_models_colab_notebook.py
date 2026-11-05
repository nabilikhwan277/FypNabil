"""Builds notebooks/open_models_colab_server.ipynb (run: python notebooks/make_open_models_colab_notebook.py).

The open-weight models (Qwen baseline, Phase 3 Fanar and SEA-LION) on Colab, with the same API, link and key as
qwen_colab_server.ipynb, so the website's "Qwen on Colab" box works unchanged. Kept as a script so the notebook
stays valid JSON.
"""
import json
from pathlib import Path

md = lambda s: {"cell_type": "markdown", "metadata": {}, "source": s.strip("\n").splitlines(keepends=True)}  # noqa: E731
code = lambda s: {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],  # noqa: E731
                  "source": s.strip("\n").splitlines(keepends=True)}

cells = [
    md("""
# Open-model server for the KAFA UPKK Learning Assistant (Google Colab + ngrok)

Experiment plan v3, **Phase 3**: the open-weight models, each served the same way so Claude can test them.

| Choice | Hugging Face model | Why | Precision |
|---|---|---|---|
| **Qwen** | `unsloth/Qwen3-4B-Instruct-2507-bnb-4bit` | the baseline: the same 4-bit model as the laptop | 4-bit on every GPU |
| **Fanar** | `QCRI/Fanar-1-9B-Instruct` (Apache-2.0) | Arabic model trained with Islamic content | 16-bit on L4/A100, 4-bit on T4 |
| **SEA-LION** | `aisingapore/Gemma-SEA-LION-v3-9B-IT` (Gemma licence) | Southeast Asian model with Malay | 16-bit on L4/A100, 4-bit on T4 |

Run the notebook **once per model**: choose the model in cell 3, Run all, paste the link, and tell Claude to run
the tests. For the next model: **Runtime → Disconnect and delete runtime**, choose the other model, Run all again
(a fresh runtime each time: two 9B models do not fit on one GPU).

**Before you start**
1. **Runtime → Change runtime type** → choose **L4 GPU** (or **A100**). Use the same GPU for every model so the
   comparison is fair. A free **T4** also works, but Fanar and SEA-LION then run in 4-bit.
2. Get a free ngrok token: sign up at https://dashboard.ngrok.com → *Your Authtoken* → copy it.
3. Add it to Colab: click the **🔑 key icon (Secrets)** on the left → *Add new secret* →
   name `NGROK_AUTHTOKEN`, value = your token → switch **Notebook access** on.

**Then:** Runtime → **Run all**. The first time takes about **10–15 minutes** (Fanar/SEA-LION are about 18 GB to
download, Qwen about 3 GB). Cell 4 ends with a **speed test**: if it says *too slow*, stop and tell Claude.
Cell 6 prints the **LINK** and **KEY**: in the website open **📊 Penilaian → Qwen on Colab**, paste both and
click **Save & test**. Then run cell 8 (keep alive) and leave the tab open.

Paid GPUs use Colab compute units: when the tests are done, run the last cell and
**Runtime → Disconnect and delete runtime**.
"""),
    md("## 1. Check the GPU"),
    code("""
!nvidia-smi --query-gpu=name,memory.total --format=csv || echo "No GPU: Runtime -> Change runtime type -> L4 or T4 GPU"
"""),
    md("## 2. Install packages"),
    code("""
!pip -q install "transformers==4.55.4" "accelerate>=1.2" "bitsandbytes>=0.45" fastapi "uvicorn[standard]" pyngrok
"""),
    md("""
## 3. Settings: choose the model here

Pick **Qwen**, **Fanar** or **SEA-LION** in the box on the right (or edit the text), then Run all.
"""),
    code("""
import secrets

MODEL = "SEA-LION"  # @param ["Qwen", "Fanar", "SEA-LION"]
MODEL_IDS = {"Qwen": "unsloth/Qwen3-4B-Instruct-2507-bnb-4bit",   # same as the laptop (backend/app/config.py)
             "Fanar": "QCRI/Fanar-1-9B-Instruct",
             "SEA-LION": "aisingapore/Gemma-SEA-LION-v3-9B-IT"}
MODEL_ID = MODEL_IDS[MODEL]
GEMMA = MODEL in ("Fanar", "SEA-LION")    # both are Gemma-2 models
PORT = 8000

# ngrok token: from Colab Secrets, otherwise asked here
try:
    from google.colab import userdata
    NGROK_AUTHTOKEN = userdata.get("NGROK_AUTHTOKEN")
except Exception:
    NGROK_AUTHTOKEN = None
if not NGROK_AUTHTOKEN:
    from getpass import getpass
    NGROK_AUTHTOKEN = getpass("Paste your ngrok authtoken: ").strip()

# Secret key for this session: the website must send it, so strangers who find the link cannot use your GPU.
API_KEY = secrets.token_urlsafe(24)
print("Settings ready. Model:", MODEL_ID)
"""),
    md("""
## 4. Load the model and test its speed (download 5–10 minutes the first time)

- **Qwen**: the ready-made 4-bit model, the same as the laptop, on every GPU.
- **Fanar / SEA-LION**: 16-bit (bfloat16, the model's own quality) on a GPU with 20 GB or more (L4, A100);
  4-bit (NF4) on a T4. Write the precision in the thesis, because 4-bit can lose some quality.

The whole model is put on the GPU (an error stops the cell if it does not fit), and PyTorch compiling is
switched off (on Gemma-2 it recompiled for every prompt and crashed the server). Each model's own chat
template is used; only if a template refuses the *system* role is it put in the first user message.
"""),
    code("""
import gc, os, time
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")   # less memory lost to fragmentation
import torch
# no torch.compile: transformers compiles Gemma-2 on its own, which recompiles for every prompt length
# (minutes per answer) and its CUDA graphs crash inside the web server's worker threads
torch._dynamo.config.disable = True
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

if "model" in globals():   # another model is still loaded (cell 4 run again after changing MODEL): free the GPU first
    del model
    gc.collect()
    torch.cuda.empty_cache()
    print(f"Unloaded the previous model; GPU memory now {torch.cuda.memory_allocated() / 1e9:.1f} GB")
torch.cuda.reset_peak_memory_stats()

gpu_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
FULL = GEMMA and gpu_gb >= 20
PRECISION = "bfloat16" if FULL else "4-bit NF4"
t0 = time.time()
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
# whole model on the GPU: "auto" keeps memory spare and can move layers to the CPU, making each answer take minutes
kw = dict(device_map={"": 0})
if GEMMA:
    kw["attn_implementation"] = "eager"      # Gemma-2 needs it for its attention soft-cap
    if FULL:
        kw["torch_dtype"] = torch.bfloat16
    else:
        kw["quantization_config"] = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                                       bnb_4bit_compute_dtype=torch.float16,
                                                       bnb_4bit_use_double_quant=True)
else:
    kw["torch_dtype"] = torch.float16       # the Qwen model is already 4-bit: same settings as the laptop
model = AutoModelForCausalLM.from_pretrained(MODEL_ID, **kw)
model.eval()
assert all(p.device.type == "cuda" for p in model.parameters()), "part of the model is not on the GPU"
if tokenizer.pad_token_id is None:
    tokenizer.pad_token_id = tokenizer.eos_token_id
# stop at the end of the model's turn (Gemma: <end_of_turn>, Qwen: <|im_end|>)
STOP = sorted({i for i in [tokenizer.eos_token_id, *tokenizer.convert_tokens_to_ids(["<end_of_turn>", "<|im_end|>"])]
               if isinstance(i, int) and i != tokenizer.unk_token_id})
print(f"Loaded {MODEL_ID} in {PRECISION} in {time.time() - t0:.0f}s on {torch.cuda.get_device_name(0)} "
      f"({gpu_gb:.0f} GB); GPU memory used {torch.cuda.memory_allocated() / 1e9:.1f} GB; stop tokens {STOP}")


def no_system(messages):
    \"\"\"For a template that rejects the system role: put it in front of the first user message.\"\"\"
    system = "\\n\\n".join(m["content"] for m in messages if m["role"] == "system")
    rest = [dict(m) for m in messages if m["role"] != "system"]
    if system:
        if rest and rest[0]["role"] == "user":
            rest[0]["content"] = f"{system}\\n\\n{rest[0]['content']}"
        else:
            rest.insert(0, {"role": "user", "content": system})
    return rest


@torch.inference_mode()
def generate(messages, max_tokens=900, temperature=0.0):
    try:
        inputs = tokenizer.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt", return_dict=True)
    except Exception:
        inputs = tokenizer.apply_chat_template(no_system(messages), add_generation_prompt=True,
                                               return_tensors="pt", return_dict=True)
    inputs = inputs.to(model.device)
    kw = dict(max_new_tokens=max_tokens, pad_token_id=tokenizer.pad_token_id, eos_token_id=STOP, disable_compile=True)
    if temperature and temperature > 0:
        kw.update(do_sample=True, temperature=temperature, top_p=0.9)
    else:
        kw.update(do_sample=False, temperature=None, top_p=None, top_k=None)   # greedy = repeatable marking
    try:
        out = model.generate(**inputs, **kw)
        n_in = inputs["input_ids"].shape[1]
        new = out[0, n_in:]
        return tokenizer.decode(new, skip_special_tokens=True).strip(), n_in, len(new)
    finally:   # free the GPU after every answer: on a 15 GB T4 a long prompt otherwise runs out of memory
        del inputs
        gc.collect()
        torch.cuda.empty_cache()


for q in ("Berapakah kadar panjang bacaan Mad Badal? Jawab dalam satu ayat.",
          "Tulis perkataan 'sekolah' dalam tulisan Jawi."):
    text, _, _ = generate([{"role": "system", "content": "Jawab dalam Bahasa Melayu."},
                           {"role": "user", "content": q}], max_tokens=60)
    print(q, "->", text)

# Speed test with a prompt as long as the marking prompts (about 3,000 tokens): one marking answer makes
# several such calls, so this must take well under a minute.
long_text = "Mad Asli ialah bacaan panjang dua harakat apabila huruf mad tidak bertemu hamzah atau sukun. " * 150
t0 = time.time()
text, n_in, n_out = generate([{"role": "system", "content": "Anda guru KAFA. Jawab ringkas."},
                              {"role": "user", "content": long_text + "\\nRingkaskan nota di atas dalam tiga ayat."}],
                             max_tokens=200)
secs = time.time() - t0
print(f"Speed test: {n_in} prompt tokens + {n_out} new tokens in {secs:.0f}s ({n_out / secs:.1f} tokens/s); "
      f"peak GPU memory {torch.cuda.max_memory_allocated() / 1e9:.1f} GB")
print("OK: fast enough" if secs < 90 else "TOO SLOW: stop here and tell Claude")
"""),
    md("""
## 5. Start the server

The same **OpenAI-style** API as the Qwen notebook (the website already speaks this format):
- `GET /health` → model name, precision and GPU
- `POST /v1/chat/completions` → `{"messages": [...], "max_tokens": 900, "temperature": 0}`

Every request needs the header `Authorization: Bearer <KEY>`. Requests are answered one at a time (one GPU).
If an answer fails, the server sends the reason back and prints it here.
"""),
    code("""
import threading, time, traceback, uuid
import uvicorn
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

app = FastAPI(title=f"{MODEL} for KAFA UPKK")
gpu_lock = threading.Lock()

class ChatRequest(BaseModel):
    messages: list[dict]
    max_tokens: int = 900
    temperature: float = 0.0
    model: str | None = None

def check_key(authorization):
    if authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="wrong or missing key")

@app.get("/health")
def health(authorization: str | None = Header(default=None)):
    check_key(authorization)
    return {"status": "ok", "model": MODEL_ID, "precision": PRECISION, "gpu": torch.cuda.get_device_name(0),
            "gpu_memory_gb": round(torch.cuda.max_memory_allocated() / 1e9, 1)}

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
    return {"id": f"chatcmpl-{uuid.uuid4().hex[:12]}", "object": "chat.completion", "model": MODEL_ID,
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
print("Server running on port", PORT)
"""),
    md("## 6. Open the ngrok link → copy LINK and KEY into the website"),
    code("""
import time
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
print(f"Model: {MODEL} ({MODEL_ID}, {PRECISION}, {torch.cuda.get_device_name(0)})")
print("Paste these on the website:  📊 Penilaian -> Qwen on Colab")
print()
print("  LINK :", PUBLIC_URL)
print("  KEY  :", API_KEY)
print("=" * 72)
"""),
    md("## 7. Self-test through the public link"),
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
    print("The link still does not reach the server: run cells 5 and 6 again. Reply was:", r.text[:300])
r = requests.post(f"{PUBLIC_URL}/v1/chat/completions", headers=h, timeout=300, json={
    "messages": [{"role": "system", "content": "Jawab ringkas dalam Bahasa Melayu."},
                 {"role": "user", "content": "Apakah maksud Ibtida'?"}], "max_tokens": 80})
if r.ok:
    print("Answer:", r.json()["choices"][0]["message"]["content"])
else:
    print(f"FAILED (HTTP {r.status_code}): {r.text[:500]}")   # copy this to Claude
print("Without the key ->", requests.get(f"{PUBLIC_URL}/health", headers={"ngrok-skip-browser-warning": "true"}).status_code,
      "(401 = protected)")
"""),
    md("""
## 8. Keep it running

Leave this tab open while Claude runs the tests (about 30–90 minutes per model), and do not let the laptop sleep.
Running the cell below keeps the session busy so Colab does not stop it for being idle (stop it with ■ when you
are done). To shut everything down, run the last cell, then **Runtime → Disconnect and delete runtime**.
"""),
    code("""
import time
try:
    while True:
        time.sleep(60)
        print(time.strftime("%H:%M"), "server alive:", PUBLIC_URL)
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
out = Path(__file__).with_name("open_models_colab_server.ipynb")
out.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
print("wrote", out)
