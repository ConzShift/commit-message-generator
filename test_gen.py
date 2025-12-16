# test_gen.py
try:
    from transformers import pipeline
    MODEL = "bigcode/santacoder"
    try:
        gen = pipeline("text-generation", model=MODEL, device=0)
    except Exception:
        gen = pipeline("text-generation", model=MODEL, device=-1)
    out = gen("Write one Conventional Commit message: Changed files: README.md", max_new_tokens=60, do_sample=False)[0]["generated_text"]
    print("GEN_OK\n", out[:400])
except Exception:
    import traceback
    traceback.print_exc()