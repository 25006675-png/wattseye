"""Live NILM runtime: rolling power window -> per-appliance watts + on/off.

Wraps the *faithful* ELECTRIcity model (`ML/NILM/electricity_model.py`, the
Discriminator — see that file for why the older test_nilm_inference.py is wrong)
so the live pipeline can disaggregate the residual signal into appliances instead
of lumping it into one "other" bucket.

HONEST CAVEATS (read before trusting live numbers):
  * VALIDATED: on a real UK-DALE House-2 kettle window with the correct stats
    (x_mean~=300, x_std~=471) the faithful model predicts ~2130 W vs 2879 W
    ground truth. The port is byte-exact vs the training repo (max diff 0.0).
  * The model is BRITTLE to normalisation. Measured: wrong stats (522/814) -> 0 W;
    self-normalising the live window -> 0 W. It only works with the UK-DALE
    training-distribution stats baked in below. You cannot make it
    calibration-free by self-normalising.
  * Live rig accuracy needs FINE-TUNING. These checkpoints learned UK-DALE's
    aggregate scale; raw demo-rig watts are off-distribution. Reported F1
    (eval/RESULTS.md) is UK-DALE House-2, not rig accuracy.
  * Input cadence should match training (6 s). We bin incoming samples to
    `bin_seconds` and left-pad the window until it fills — so it runs immediately
    but is most accurate once enough real history has accumulated.
  * DEMO GUIDANCE: live per-appliance NILM is best-effort, NOT the hero. The
    reliable live moment is the empty-room cutoff; breadth comes from replaying
    recorded per-appliance data. Label live NILM tiles as best-effort.

This module degrades safely: if torch or the checkpoints are missing, the caller
should fall back to the aggregate "other" bucket (pi_bridge already does).
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "ML" / "NILM"

# UK-DALE training constants (config.py + eval/RESULTS.md). cutoff scales the
# model output back to watts; threshold sets the on/off line.
CUTOFF_W = {"kettle": 3100, "fridge": 300, "washing_machine": 2500, "hair_dryer": 2500, "iron": 2500}
ON_THRESHOLD_W = {"kettle": 2000, "fridge": 50, "washing_machine": 20, "hair_dryer": 800, "iron": 1000}
WINDOW = 480
# UK-DALE training-distribution aggregate stats (recovered by running the parser
# on House 2). The model only produces sane output with these — see caveats above.
# For a real deployment, recompute from the environment's own aggregate and/or
# fine-tune; do NOT self-normalise the window (measured to give 0 W).
X_MEAN = 300.6
X_STD = 471.2


class NilmRunner:
    """Buffers an aggregate (residual) power signal and disaggregates on demand."""

    def __init__(self, appliances: list[str] | None = None, model_dir: Path = MODEL_DIR,
                 bin_seconds: float = 6.0, x_mean: float = X_MEAN, x_std: float = X_STD) -> None:
        import torch  # raises if unavailable -> caller falls back
        from ML.NILM.electricity_model import load_electricity

        self._torch = torch
        self.bin_seconds = bin_seconds
        self.x_mean = x_mean
        self.x_std = x_std

        names = appliances or [p.stem for p in sorted(model_dir.glob("*.pth"))]
        self.models = {}
        for name in names:
            path = model_dir / f"{name}.pth"
            if path.exists():
                self.models[name] = load_electricity(path, device="cpu")
        if not self.models:
            raise FileNotFoundError(f"no NILM checkpoints found in {model_dir}")

        self._bins: list[float] = []
        self._bin_accum = 0.0
        self._bin_count = 0
        self._bin_started: float | None = None

    def add_sample(self, watts: float, ts_epoch: float) -> None:
        """Feed one raw reading; aggregated into fixed `bin_seconds` bins."""
        if self._bin_started is None:
            self._bin_started = ts_epoch
        self._bin_accum += watts
        self._bin_count += 1
        if ts_epoch - self._bin_started >= self.bin_seconds:
            self._bins.append(self._bin_accum / max(1, self._bin_count))
            self._bins = self._bins[-WINDOW:]
            self._bin_accum = 0.0
            self._bin_count = 0
            self._bin_started = ts_epoch

    def _window(self) -> list[float]:
        bins = list(self._bins)
        if not bins:
            return [0.0] * WINDOW
        if len(bins) < WINDOW:  # left-pad with the earliest value so it runs early
            bins = [bins[0]] * (WINDOW - len(bins)) + bins
        return bins[-WINDOW:]

    def infer(self) -> dict[str, dict]:
        """Return {appliance: {"watts": float, "on": bool}} for each model."""
        torch = self._torch
        window = self._window()
        x = torch.tensor(window, dtype=torch.float32).view(1, 1, WINDOW)
        x = (x - self.x_mean) / self.x_std

        out: dict[str, dict] = {}
        with torch.no_grad():
            for name, model in self.models.items():
                seq = model(x)                       # [1, 1, 480] Discriminator output
                mid = float(seq[0, 0, seq.shape[-1] // 2])
                watts = mid * CUTOFF_W.get(name, 1000)
                watts = 0.0 if watts < 5 else min(watts, CUTOFF_W.get(name, watts))
                out[name] = {
                    "watts": round(max(0.0, watts), 1),
                    "on": watts >= ON_THRESHOLD_W.get(name, 50),
                }
        return out


def try_build_runner(**kw) -> "NilmRunner | None":
    """Build a runner, or None if torch/checkpoints are unavailable (safe fallback)."""
    try:
        return NilmRunner(**kw)
    except Exception:
        return None


if __name__ == "__main__":
    # PLUMBING check only: confirms add_sample -> infer runs and returns a
    # numeric reading per model. It does NOT assert a specific detection —
    # synthetic flat blocks misrepresent appliance *shape* (a flat 40-min 2.4 kW
    # block reads as a sustained heater, not a kettle pulse). Real accuracy is
    # validated on genuine UK-DALE windows (kettle ~2130 W vs 2879 W gt), not here.
    runner = try_build_runner(bin_seconds=1.0)
    if runner is None:
        raise SystemExit("torch / checkpoints unavailable")
    t = 0.0
    for w in [400.0] * 120 + [2400.0] * 400:
        runner.add_sample(w, t)
        t += 1.0
    result = runner.infer()
    assert len(result) == len(runner.models), "every model should return a reading"
    assert all(isinstance(r["watts"], float) for r in result.values())
    print(f"plumbing OK — {len(result)} models inferred:")
    for name, r in sorted(result.items(), key=lambda kv: -kv[1]["watts"]):
        print(f"  {name:16s} {r['watts']:8.1f} W  {'ON' if r['on'] else 'off'}")
