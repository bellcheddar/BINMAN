# Serving BINMAN-LM on HuggingFace ZeroGPU

Everything here is scaffolded and tested as far as it can be without a CUDA
machine. The steps needing your account are marked **you**.

## The adapter repository is public, by your decision

Recorded as D-030. The one thing it runs against, stated once so it is on the
record rather than buried: PROTAC-DB's terms read "internal use only,
derivatives included; redistribution prohibited", and a trained adapter is a
derivative. That clause covers the weights whether or not the source data is
shared, so "the input data is not shared" does not by itself clear it.

Your call, made with the reasoning in D-030: non-commercial, source credited,
no dataset redistributed. If you later want it airtight rather than defensible,
rebuilding Task B's `protac` class from a redistributable source would remove
the question entirely, at the cost of the glue-against-PROTAC confusion the
confusion matrix exists to expose.

## 1. Convert the MLX adapter to PEFT

```bash
pixi run python lm/export_hf.py --adapter models/binman-lm/adapters \
                                --out models/binman-lm/hf-adapter --verify
```

`--verify` runs the real held-out test questions through the converted adapter
and prints the same metrics `lm/evaluate.py` reports. **Compare them before
shipping.** The adapter was trained to correct a 4-bit quantised base and will
be applied to a 16-bit one; nothing guarantees the correction transfers, and an
adapter that loads cleanly but answers badly is exactly the failure that
produced D-016. Without a CUDA box the verification runs on MPS, which is the
same numerics the Space will use (float16) on different hardware.

## 2. Authenticate (**you**, once)

This is the only step that needs you. Run it in the Claude Code session with a
leading `!` so the output lands in the conversation:

```
!pip install -U "huggingface_hub[cli]" && hf auth login
```

Paste a token with **write** scope when prompted. It is stored in the
HuggingFace CLI's own credential store, which means the rest of the deployment
can run without the token ever being read, printed or committed.

Searching your other projects for a token was blocked by the sandbox's
credential guard, which is the right behaviour: `hf auth login` is the safer
route and needs doing once.

## 3. Create and upload both repositories

The CLI changed in huggingface_hub 2.x: it is `hf repos create`, not
`hf repo create`, and hardware is settable from the CLI rather than only the
web UI, so there is no manual step left.

```bash
hf repos create Dellboy/binman-lm-adapter --type model --public
hf repos create Dellboy/binman-lm --type space --sdk gradio --public
hf spaces settings Dellboy/binman-lm --hardware zero-a10g

hf upload Dellboy/binman-lm deploy/hf-space . --repo-type space
hf upload Dellboy/binman-lm-adapter models/binman-lm/hf-adapter . --repo-type model
```

Three things the Hub rejects that are worth knowing before you hit them:

- **Space card colours** are a fixed list. `orange` is not on it; `yellow` is
  the nearest to the Depot sodium amber.
- **`short_description`** is capped at 60 characters, and a colon inside it
  must be quoted or the YAML front matter fails to parse.
- **torch must be a ZeroGPU-supported build** (2.8.0 and up at the time of
  writing). An older pin fails at config time with `CONFIG_ERROR` before the
  Space ever builds. `gradio` is deliberately absent from `requirements.txt`:
  the runtime installs the version named by `sdk_version` in the Space card.

Verify with `hf spaces info Dellboy/binman-lm`, which reports the runtime stage
and any `errorMessage`.

## 4. What the Space serves

The three text jobs and nothing else: query translation, evidence triage and
abstention. The atlas is not served. It is 142 MB and several source datasets
carry licences that do not permit redistribution, so the Space demonstrates
what the model produces and the repository shows what the pipeline computes.

The model never computes, estimates or reports a number. The abstention tab is
as much the demonstration as the query tab, because a model that will invent a
dSASA is the failure mode the project exists to avoid.

## Known risk, stated plainly

Quantisation transfer is the one thing that cannot be checked from here. If
`--verify` shows the converted adapter scoring materially below the MLX
numbers, the honest options are to train a LoRA against the 16-bit base for
serving, or to serve the MLX adapter from Apple hardware instead and leave
ZeroGPU alone. Do not ship a degraded adapter and quote the MLX metrics beside
it.
