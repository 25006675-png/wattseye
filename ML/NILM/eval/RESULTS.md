# WattsEye NILM — Verified Test Results

These are the accuracy numbers behind the pitch-deck claim *"F1 on unseen-house:
Kettle 0.96 · Fridge 0.86 · Washing machine 0.80 · Hair dryer 0.76 · Iron 0.68."*
They are reproduced here so they are **openable and auditable during judging**,
without needing a GPU or the full training pipeline.

## Headline numbers (UK-DALE, unseen House 2)

| Appliance | F1 | Precision | Recall | Accuracy | MAE (W) | Test samples |
|---|---|---|---|---|---|---|
| Kettle | **0.960** | 0.976 | 0.945 | 0.999 | 7.8 | 1,925,760 |
| Fridge | **0.858** | 0.911 | 0.811 | 0.883 | 20.0 | 1,513,920 |
| Washing machine | **0.802** | 0.769 | 0.838 | 0.995 | 4.2 | 1,513,920 |
| Hair dryer | **0.762** | 0.865 | 0.680 | 0.988 | 22.3 | 43,200 |
| Iron | **0.675** | 0.664 | 0.688 | 0.923 | 162.7 | 960 |

Machine-readable copy: [`nilm_test_metrics.json`](nilm_test_metrics.json).

These five appliances correspond exactly to the five shipped checkpoints
(`ML/NILM/{kettle,fridge,washing_machine,hair_dryer,iron}.pth`). The shipped
`kettle.pth` is **byte-identical** (SHA-256) to the training-repo checkpoint, so
the deployed weights are the evaluated weights.

## Method

- **Model:** ELECTRIcity (Sykiotis et al., 2022) — a Transformer seq2seq NILM
  network. Trained config: `window_size=480`, `window_stride=240`,
  Discriminator `hidden=256`, Generator `hidden=64`, `heads=2`, `n_layers=2`.
  The disaggregation prediction at inference is the **Discriminator** output.
- **Data:** UK-DALE, resampled to a 6-second grid, mean-normalised with
  training-set μ/σ (≈522 / ≈814 W).
- **Split (unseen-house protocol):** train on all UK-DALE houses **except House
  2**; first 10% of the training pool held out for validation; House 2 used only
  for the final test. Appliances available in a single house use an 80/20
  chronological split instead.
- **Scoring:** ground-truth ON/OFF derived from sub-meter power via threshold +
  `min_on`/`min_off` smoothing; predicted ON/OFF via a power threshold. F1/MAE
  per the training repo's `metrics.py`. Per-appliance thresholds are in
  `nilm_test_metrics.json`.

## Reproduce

The training repo saves the held-out House-2 predictions per appliance as
`<appliance>/test_result.json` (`{"gt": [...watts...], "pred": [...watts...]}`).
Point the verifier at that directory:

```bash
python ML/NILM/eval/verify_f1.py --pred-root <training_repo>/checkpoints_electricity/uk_dale
# or a single appliance:
python ML/NILM/eval/verify_f1.py --file kettle/test_result.json --appliance kettle
```

The script recomputes the table above from the saved predictions using the exact
status logic, and prints `OK` next to each appliance whose F1 matches the
published value (it does for all five).

> The raw `test_result.json` prediction dumps are ~100 MB each and live in the
> training repo, not here — only the verifier, the per-appliance constants, and
> the compact verified metrics are vendored into this repo.

## Honest caveats

- **Test vs live.** These are dataset accuracy figures on held-out UK-DALE data,
  not live-demo accuracy. Real-home deployment needs sensor calibration and
  fine-tuning (see `plan/03_MACHINE_LEARNING.md`). The live demo proves the
  pipeline/architecture; NILM accuracy is an offline metric.
- **Small supports.** Hair dryer (43,200 samples) and especially iron (960) have
  small test supports in House 2, so those two F1 values are noisier than
  kettle/fridge/washing machine.
- **AC is not in this table on purpose.** Inverter AC has no clean NILM
  signature; WattsEye measures it with a dedicated CT clamp instead of NILM.

## Inference correctness note (for engineers)

`ML/NILM/electricity_model.py` is the **faithful** architecture and loads the
shipped `.pth` files with `strict=True`. Use it for any inference that must match
the numbers above. The older `ML/NILM/test_nilm_inference.py` is an *approximate*
reconstruction (wrong sub-network + wrong hyper-parameters) kept only as a
load/latency smoke test — it does **not** reproduce these metrics. See the
docstring in `electricity_model.py` for the specifics.
