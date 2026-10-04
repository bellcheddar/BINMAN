# Serving BINMAN-LM on HuggingFace ZeroGPU

Everything here is scaffolded and tested as far as it can be without a CUDA
machine. The steps needing your account are marked **you**.

## Why the adapter repository is private

Gate G4 authorised a public code repository. It did not authorise publishing
the model, and your licence decision for PROTAC-DB was explicit: *"we are not
distributing the model, just using it"* (DECISIONS D-021). The adapter is
trained on Task B data derived from PROTAC-DB, whose terms permit internal use
including derivatives but prohibit redistribution. A public weights repository
would be redistribution.

A **private** adapter repository that only the Space can read keeps that
position intact: the Space serves inference, the weights are not published, and
the sources are cited. See D-029.

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

## 2. Create the private adapter repository (**you**)

The session token has `contribute-repos` but repository creation is not exposed
through the connector, so this is yours to run:

```bash
pip install -U "huggingface_hub[cli]"
hf auth login
hf repo create binman-lm-adapter --repo-type model --private
hf upload Dellboy/binman-lm-adapter models/binman-lm/hf-adapter . --repo-type model
```

## 3. Create the Space (**you**)

```bash
hf repo create binman-lm --repo-type space --space_sdk gradio
hf upload Dellboy/binman-lm deploy/hf-space . --repo-type space
```

Then in the Space settings:

- **Hardware**: ZeroGPU (your account is PRO, so this is available)
- **Secret** `HF_TOKEN`: a read token with access to the private adapter repo
- **Variable** `BINMAN_ADAPTER_REPO`: `Dellboy/binman-lm-adapter` (only if the
  name differs from the default)

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
