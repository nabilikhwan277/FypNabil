"""Builds notebooks/qwen_colab_server.ipynb (run: python notebooks/make_qwen_colab_notebook.py).

Kept as a script so the notebook stays valid JSON and easy to review in git.
"""
import json
from pathlib import Path

md = lambda s: {"cell_type": "markdown", "metadata": {}, "source": s.strip("\n").splitlines(keepends=True)}  # noqa: E731
code = lambda s: {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],  # noqa: E731
                  "source": s.strip("\n").splitlines(keepends=True)}

cells = [
    md("""
# Qwen3-4B server for the KAFA UPKK Learning Assistant (Google Colab + ngrok)

This notebook runs the open-weight model **Qwen3-4B-Instruct-2507** (the experiment model `qwen`, and the
*Tanya Bulan* chat) on Colab's free GPU instead of your laptop, and gives you a **link** and a **key** to paste
into the website.

**Before you start**
1. **Runtime → Change runtime type → T4 GPU** → Save.
2. Get a free ngrok token: sign up at https://dashboard.ngrok.com → *Your Authtoken* → copy it.
3. Add it to Colab: click the **🔑 key icon (Secrets)** on the left → *Add new secret* →
   name `NGROK_AUTHTOKEN`, value = your token → switch **Notebook access** on.
   (If you skip this, cell 3 will ask you to paste the token.)

**Then:** Runtime → **Run all** (about 3–5 minutes the first time). At the end, cell 6 prints the
**LINK** and **KEY**. In the website open **📊 Penilaian → Qwen on Colab**, paste both, and click **Save & test**.

Keep this tab open while you use the website. Free Colab stops after about 90 minutes without activity
or 12 hours in total; then run all cells again (you get a **new link**, so paste it again).
"""),
    md("## 1. Check the GPU"),
    code("""
!nvidia-smi --query-gpu=name,memory.total --format=csv || echo "No GPU: Runtime -> Change runtime type -> T4 GPU"
"""),
    md("## 2. Install packages"),
    code("""
!pip -q install "transformers==4.55.4" "accelerate>=1.2" "bitsandbytes>=0.45" fastapi "uvicorn[standard]" pyngrok
"""),
    md("""
## 3. Settings

`MODEL_ID` is the **same 4-bit model as on the laptop**, so results are comparable. On a T4 you could also use the
full-precision `Qwen/Qwen3-4B-Instruct-2507` (about 8 GB), but then say so in the thesis.
"""),
    code("""
import secrets

MODEL_ID = "unsloth/Qwen3-4B-Instruct-2507-bnb-4bit"   # same as the laptop (backend/app/config.py)
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
    md("## 4. Load Qwen3-4B (about 1–2 minutes)"),
    code("""
import time, torch
from transformers import AutoModelForCausalLM, AutoTokenizer

t0 = time.time()
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
model = AutoModelForCausalLM.from_pretrained(MODEL_ID, device_map="auto", torch_dtype=torch.float16)
model.eval()
if tokenizer.pad_token_id is None:
    tokenizer.pad_token_id = tokenizer.eos_token_id
print(f"Loaded in {time.time() - t0:.0f}s on {torch.cuda.get_device_name(0)}; "
      f"GPU memory used {torch.cuda.memory_allocated() / 1e9:.1f} GB")

@torch.inference_mode()
def generate(messages, max_tokens=900, temperature=0.0):
    inputs = tokenizer.apply_chat_template(messages, add_generation_prompt=True,
                                           return_tensors="pt", return_dict=True).to(model.device)
    kw = dict(max_new_tokens=max_tokens, pad_token_id=tokenizer.pad_token_id)
    if temperature and temperature > 0:
        kw.update(do_sample=True, temperature=temperature, top_p=0.9)
    else:
        kw.update(do_sample=False, temperature=None, top_p=None, top_k=None)   # greedy = repeatable marking
    out = model.generate(**inputs, **kw)
    n_in = inputs["input_ids"].shape[1]
    new = out[0, n_in:]
    return tokenizer.decode(new, skip_special_tokens=True).strip(), n_in, len(new)

text, _, _ = generate([{"role": "user", "content": "Berapakah kadar panjang bacaan Mad Badal? Jawab dalam satu ayat."}],
                      max_tokens=60)
print("Test answer:", text)
"""),
    md("""
## 5. Start the server

An **OpenAI-style** API (the website already speaks this format):
- `GET /health` → model name
- `POST /v1/chat/completions` → `{"messages": [...], "max_tokens": 900, "temperature": 0}`

Every request needs the header `Authorization: Bearer <KEY>`. Requests are answered one at a time (one GPU).
"""),
    code("""
import threading, time, uuid
import uvicorn
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Qwen3-4B for KAFA UPKK")
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
    return {"status": "ok", "model": MODEL_ID, "gpu": torch.cuda.get_device_name(0)}

@app.post("/v1/chat/completions")
def chat_completions(req: ChatRequest, authorization: str | None = Header(default=None)):
    check_key(authorization)
    max_tokens = max(1, min(req.max_tokens, 2048))
    with gpu_lock:
        t0 = time.time()
        text, n_in, n_out = generate(req.messages, max_tokens, req.temperature)
    return {"id": f"chatcmpl-{uuid.uuid4().hex[:12]}", "object": "chat.completion", "model": MODEL_ID,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": text},
                         "finish_reason": "length" if n_out >= max_tokens else "stop"}],
            "usage": {"prompt_tokens": n_in, "completion_tokens": n_out, "total_tokens": n_in + n_out},
            "latency_ms": int((time.time() - t0) * 1000)}

server = uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=PORT, log_level="warning"))
threading.Thread(target=server.run, daemon=True).start()
time.sleep(3)
print("Server running on port", PORT)
"""),
    md("## 6. Open the ngrok link → copy LINK and KEY into the website"),
    code("""
from pyngrok import ngrok

ngrok.set_auth_token(NGROK_AUTHTOKEN)
ngrok.kill()                                  # close an old tunnel if this cell is run again
PUBLIC_URL = ngrok.connect(PORT, "http").public_url

print("=" * 72)
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
print(requests.get(f"{PUBLIC_URL}/health", headers=h, timeout=30).json())
r = requests.post(f"{PUBLIC_URL}/v1/chat/completions", headers=h, timeout=120, json={
    "messages": [{"role": "user", "content": "Apakah maksud Ibtida'? Jawab ringkas."}], "max_tokens": 80})
print(r.json()["choices"][0]["message"]["content"])
print("Without the key ->", requests.get(f"{PUBLIC_URL}/health", headers={"ngrok-skip-browser-warning": "true"}).status_code,
      "(401 = protected)")
"""),
    md("""
## 8. Keep it running

Leave this tab open. Running the cell below keeps the session busy so Colab does not stop it for being idle
(stop it with ■ when you are done). To shut everything down, run the last cell.
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

nb = {"cells": cells, "metadata": {"accelerator": "GPU", "colab": {"provenance": [], "gpuType": "T4"},
                                    "kernelspec": {"display_name": "Python 3", "name": "python3"},
                                    "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 0}
out = Path(__file__).with_name("qwen_colab_server.ipynb")
out.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
print("wrote", out)
