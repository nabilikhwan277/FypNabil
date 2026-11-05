"""An open-weight model answers only when the Colab link serves that very model (no network: faked)."""
import pytest

from backend.app import remote_llm
from backend.app.llm_api import MODELS, LLMError, complete, open_model_problem


@pytest.fixture
def colab(monkeypatch):
    def serve(model_id, precision=None):
        monkeypatch.setattr(remote_llm, "endpoint", lambda: ("https://x.ngrok.app", "k") if model_id is not None else None)
        info = {"model": model_id, **({"precision": precision} if precision else {})} if model_id else {}
        monkeypatch.setattr(remote_llm, "served", lambda: info)
    return serve


def test_each_open_model_needs_its_own_server(colab):
    colab("QCRI/Fanar-1-9B-Instruct")
    assert open_model_problem(MODELS["fanar"]) == ""
    assert "not SEA-LION" in open_model_problem(MODELS["sealion"])
    assert "not Qwen" in open_model_problem(MODELS["qwen"])
    colab("unsloth/Qwen3-4B-Instruct-2507-bnb-4bit")
    assert open_model_problem(MODELS["qwen"]) == ""
    assert open_model_problem(MODELS["fanar"])


def test_finetuned_qwen_is_not_the_base_qwen(colab):
    colab("kafa/qwen3-4b-marker-r8e1")
    assert open_model_problem(MODELS["qwen_ft_r8e1"]) == ""
    assert open_model_problem(MODELS["qwen"])           # else its answers would be cached as the base model's
    assert open_model_problem(MODELS["qwen_ft_r16e2"])


def test_no_link_means_no_colab_model(colab):
    colab(None)
    assert "Start the Colab notebook" in open_model_problem(MODELS["fanar"])


def test_wrong_model_is_never_called_or_cached(colab, monkeypatch, tmp_path):
    from backend.app import config
    monkeypatch.setattr(config.get_settings(), "llm_cache_dir", tmp_path)
    colab("aisingapore/Gemma-SEA-LION-v3-9B-IT")
    with pytest.raises(LLMError, match="not Fanar"):
        complete("fanar", [{"role": "user", "content": "x"}], tag="test")
    assert not list(tmp_path.rglob("*.json"))


def test_4bit_and_16bit_answers_are_cached_apart(colab, monkeypatch, tmp_path):
    from backend.app import config, llm
    monkeypatch.setattr(config.get_settings(), "llm_cache_dir", tmp_path)
    calls = []
    monkeypatch.setattr(llm, "generate_text", lambda msgs, max_new_tokens: calls.append(1) or llm.Generation(
        text="ok", latency_ms=1, prompt_tokens=1, new_tokens=1))
    msgs = [{"role": "user", "content": "x"}]
    colab("aisingapore/Gemma-SEA-LION-v3-9B-IT", "4-bit NF4")
    complete("sealion", msgs)
    complete("sealion", msgs)                      # same precision: from the cache
    colab("aisingapore/Gemma-SEA-LION-v3-9B-IT", "bfloat16")
    complete("sealion", msgs)                      # other precision: asked again
    assert len(calls) == 2
    colab(None)                                    # link gone: no answer, not even from the cache
    with pytest.raises(LLMError):
        complete("sealion", msgs)
