"""
Live-style inference test for WattsEye NILM PyTorch checkpoints.

This script answers the practical question after training/evaluation:
"Can the saved .pth model load and produce a prediction from a rolling
power window fast enough for the prototype?"

Examples:
    python ML/NILM/test_nilm_inference.py --model ML/NILM/kettle.pth
    python ML/NILM/test_nilm_inference.py --all
    python ML/NILM/test_nilm_inference.py --all --csv readings.csv --power-column total_power_watts

If the model was trained with normalized inputs, pass the same values used
during training:
    --input-mean 522.1 --input-std 814.7 --output-mean 96.2 --output-std 410.5
"""

from __future__ import annotations

import argparse
import csv
import time
from collections import OrderedDict
from pathlib import Path

try:
    import torch
    from torch import Tensor, nn
except ModuleNotFoundError as exc:  # pragma: no cover - user environment check
    raise SystemExit(
        "PyTorch is required for .pth inference.\n"
        "Install it first, for example:\n"
        "  python -m pip install torch\n"
    ) from exc


DEFAULT_WINDOW_SIZE = 240
MODEL_DIR = Path(__file__).resolve().parent


class PositionalEmbedding(nn.Module):
    def __init__(self, max_len: int = DEFAULT_WINDOW_SIZE, d_model: int = 64) -> None:
        super().__init__()
        self.pe = nn.Embedding(max_len, d_model)

    def forward(self, x: Tensor) -> Tensor:
        positions = torch.arange(x.size(1), device=x.device).unsqueeze(0)
        return x + self.pe(positions)


class MultiHeadedAttention(nn.Module):
    def __init__(self, h: int = 8, d_model: int = 64) -> None:
        super().__init__()
        if d_model % h != 0:
            raise ValueError("d_model must be divisible by h")
        self.h = h
        self.d_k = d_model // h
        self.linear_layers = nn.ModuleList([nn.Linear(d_model, d_model) for _ in range(3)])
        self.output_linear = nn.Linear(d_model, d_model)

    def forward(self, x: Tensor) -> Tensor:
        batch_size = x.size(0)
        query, key, value = [
            layer(x).view(batch_size, -1, self.h, self.d_k).transpose(1, 2)
            for layer in self.linear_layers
        ]

        scores = torch.matmul(query, key.transpose(-2, -1)) / (self.d_k**0.5)
        attention = torch.softmax(scores, dim=-1)
        attended = torch.matmul(attention, value)
        attended = attended.transpose(1, 2).contiguous().view(batch_size, -1, self.h * self.d_k)
        return self.output_linear(attended)


class PositionwiseFeedForward(nn.Module):
    def __init__(self, d_model: int = 64, d_ff: int = 256) -> None:
        super().__init__()
        self.w_1 = nn.Linear(d_model, d_ff)
        self.w_2 = nn.Linear(d_ff, d_model)

    def forward(self, x: Tensor) -> Tensor:
        return self.w_2(torch.relu(self.w_1(x)))


class SublayerConnection(nn.Module):
    def __init__(self, size: int = 64) -> None:
        super().__init__()
        self.layer_norm = nn.LayerNorm(size)

    def forward(self, x: Tensor, sublayer: nn.Module) -> Tensor:
        return x + sublayer(self.layer_norm(x))


class TransformerBlock(nn.Module):
    def __init__(self, d_model: int = 64, h: int = 8, d_ff: int = 256) -> None:
        super().__init__()
        self.attention = MultiHeadedAttention(h=h, d_model=d_model)
        self.feed_forward = PositionwiseFeedForward(d_model=d_model, d_ff=d_ff)
        self.input_sublayer = SublayerConnection(size=d_model)
        self.output_sublayer = SublayerConnection(size=d_model)

    def forward(self, x: Tensor) -> Tensor:
        x = self.input_sublayer(x, self.attention)
        return self.output_sublayer(x, self.feed_forward)


class NILMGenerator(nn.Module):
    """Generator half of the saved NILM checkpoint.

    The layer names and dimensions match the current .pth files in this repo.
    If the original training code is available later, prefer replacing this
    with that exact class.
    """

    def __init__(self, window_size: int = DEFAULT_WINDOW_SIZE) -> None:
        super().__init__()
        self.conv = nn.Conv1d(1, 64, kernel_size=5, padding=2)
        self.position = PositionalEmbedding(max_len=window_size, d_model=64)
        self.layer_norm = nn.LayerNorm(64)
        self.transformer_blocks = nn.ModuleList([TransformerBlock() for _ in range(2)])
        self.deconv = nn.ConvTranspose1d(64, 64, kernel_size=4)
        self.linear1 = nn.Linear(64, 128)
        self.linear2 = nn.Linear(128, 1)

    def forward(self, x: Tensor) -> Tensor:
        if x.ndim == 1:
            x = x.unsqueeze(0)
        if x.ndim != 2:
            raise ValueError(f"Expected input shape [batch, window], got {tuple(x.shape)}")

        x = x.unsqueeze(1)
        x = self.conv(x).transpose(1, 2)
        x = self.position(x)
        x = self.layer_norm(x)
        for block in self.transformer_blocks:
            x = block(x)

        x = self.deconv(x.transpose(1, 2))
        x = x.mean(dim=2)
        x = torch.relu(self.linear1(x))
        return self.linear2(x).squeeze(-1)


def load_generator(checkpoint_path: Path, device: torch.device, window_size: int) -> NILMGenerator:
    checkpoint = torch.load(checkpoint_path, map_location=device)
    state_dict = checkpoint.get("state_dict", checkpoint.get("model_state_dict", checkpoint))
    if not isinstance(state_dict, (dict, OrderedDict)):
        raise TypeError(f"Unsupported checkpoint payload in {checkpoint_path}")

    generator_state = OrderedDict()
    for key, value in state_dict.items():
        if key.startswith("Generator."):
            generator_state[key.removeprefix("Generator.")] = value

    if not generator_state:
        raise ValueError(f"No Generator.* weights found in {checkpoint_path}")

    model = NILMGenerator(window_size=window_size).to(device)
    model.load_state_dict(generator_state, strict=True)
    model.eval()
    return model


def read_power_window(csv_path: Path, column: str, window_size: int) -> list[float]:
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if column not in (reader.fieldnames or []):
            raise ValueError(f"Column {column!r} not found. Available: {reader.fieldnames}")
        values = [float(row[column]) for row in reader if row.get(column)]

    if not values:
        raise ValueError(f"No numeric readings found in {csv_path}")
    if len(values) < window_size:
        values = [values[0]] * (window_size - len(values)) + values
    return values[-window_size:]


def synthetic_window(window_size: int) -> list[float]:
    baseline = [120.0] * window_size
    start = int(window_size * 0.55)
    stop = int(window_size * 0.75)
    for idx in range(start, stop):
        baseline[idx] += 1800.0
    return baseline


def run_one(
    model_path: Path,
    window: list[float],
    device: torch.device,
    args: argparse.Namespace,
) -> dict[str, float | str | tuple[int, ...]]:
    x = torch.tensor(window, dtype=torch.float32, device=device)
    x = (x - args.input_mean) / args.input_std
    x = x.unsqueeze(0)

    model = load_generator(model_path, device=device, window_size=len(window))

    with torch.no_grad():
        for _ in range(args.warmup):
            _ = model(x)

        start = time.perf_counter()
        prediction = model(x)
        if device.type == "cuda":
            torch.cuda.synchronize()
        elapsed_ms = (time.perf_counter() - start) * 1000

    output = float(prediction.item())
    output_watts = output * args.output_std + args.output_mean
    return {
        "model": model_path.name,
        "input_shape": tuple(x.shape),
        "raw_output": round(output, 4),
        "predicted_watts": round(max(0.0, output_watts), 2),
        "inference_ms": round(elapsed_ms, 3),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test live-style NILM inference from .pth models.")
    parser.add_argument("--model", type=Path, help="Path to one .pth model.")
    parser.add_argument("--all", action="store_true", help="Run every .pth model in ML/NILM.")
    parser.add_argument("--csv", type=Path, help="Optional CSV containing live/sample power readings.")
    parser.add_argument("--power-column", default="total_power_watts", help="CSV column to use as input power.")
    parser.add_argument("--window-size", type=int, default=DEFAULT_WINDOW_SIZE)
    parser.add_argument("--input-mean", type=float, default=0.0)
    parser.add_argument("--input-std", type=float, default=1.0)
    parser.add_argument("--output-mean", type=float, default=0.0)
    parser.add_argument("--output-std", type=float, default=1.0)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    parser.add_argument("--warmup", type=int, default=3)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.input_std == 0 or args.output_std == 0:
        raise ValueError("input/output std cannot be zero")

    if args.csv:
        window = read_power_window(args.csv, args.power_column, args.window_size)
    else:
        window = synthetic_window(args.window_size)

    if args.all:
        model_paths = sorted(MODEL_DIR.glob("*.pth"))
    elif args.model:
        model_paths = [args.model]
    else:
        model_paths = [MODEL_DIR / "kettle.pth"]

    device = torch.device(args.device)
    rows = [run_one(path, window, device, args) for path in model_paths]

    print("model,input_shape,raw_output,predicted_watts,inference_ms")
    for row in rows:
        print(
            f"{row['model']},{row['input_shape']},"
            f"{row['raw_output']},{row['predicted_watts']},{row['inference_ms']}"
        )


if __name__ == "__main__":
    main()
