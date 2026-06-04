"""Faithful ELECTRIcity model definition for the shipped WattsEye NILM checkpoints.

This is the *exact* architecture the `ML/NILM/*.pth` checkpoints were trained
with (ported from the training repo's `model_helpers.py` + `Electricity_model.py`).
Use this — not the approximate reconstruction in `test_nilm_inference.py` — when
you need predictions that match the reported F1/MAE in `eval/RESULTS.md`.

Two things that the older `test_nilm_inference.py` got wrong, documented here so
nobody re-introduces them:

1. The disaggregation prediction at inference time is the **Discriminator**
   (hidden=256), NOT the Generator (hidden=64). At test time the training code
   runs `ELECTRICITY.forward(x)` with `pretrain=False`, which returns the
   Discriminator output. The Generator is only used during masked pre-training.
   Loading only the `Generator.*` weights gives the wrong sub-network.

2. The trained config is `window_size=480, window_stride=240, hidden=256
   (discriminator), heads=2, n_layers=2`, with an `LPPool1d` token downsample,
   GELU feed-forward, post-norm sublayers, and a sequence (seq2seq) output —
   none of which the reconstruction matched.

Checkpoint layout (per appliance .pth, a plain state_dict):
    Discriminator.*   hidden=256   <- the inference network
    Generator.*       hidden=64    <- pre-training only

Input/normalization (UK-DALE, `normalize='mean'`):
    x_norm = (aggregate_watts - x_mean) / x_std        # x_mean≈522, x_std≈814
    pred_watts = min(relu(model_out) * cutoff, cutoff) # cutoff per appliance
    on/off     = pred_watts >= threshold               # threshold per appliance
See eval/RESULTS.md for the per-appliance cutoff/threshold table.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import torch
import torch.nn.functional as F
from torch import nn


# --------------------------------------------------------------------------- #
# Building blocks (ported verbatim from the training repo's model_helpers.py)
# --------------------------------------------------------------------------- #
class GELU(nn.Module):
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return 0.5 * x * (1 + torch.tanh(math.sqrt(2 / math.pi) * (x + 0.044715 * torch.pow(x, 3))))


class PositionalEmbedding(nn.Module):
    def __init__(self, max_len: int, d_model: int) -> None:
        super().__init__()
        self.pe = nn.Embedding(max_len, d_model)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch_size = x.size(0)
        return self.pe.weight.unsqueeze(0).repeat(batch_size, 1, 1)


class LayerNorm(nn.Module):
    def __init__(self, features: int, eps: float = 1e-6) -> None:
        super().__init__()
        self.weight = nn.Parameter(torch.ones(features))
        self.bias = nn.Parameter(torch.zeros(features))
        self.eps = eps

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        mean = x.mean(-1, keepdim=True)
        std = x.std(-1, keepdim=True)
        return self.weight * (x - mean) / (std + self.eps) + self.bias


class Attention(nn.Module):
    def forward(self, query, key, value, mask=None, dropout=None):
        scores = torch.matmul(query, key.transpose(-2, -1)) / math.sqrt(query.size(-1))
        if mask is not None:
            scores = scores.masked_fill(mask == 0, -1e9)
        p_attn = F.softmax(scores, dim=-1)
        if dropout is not None:
            p_attn = dropout(p_attn)
        return torch.matmul(p_attn, value), p_attn


class MultiHeadedAttention(nn.Module):
    def __init__(self, h: int, d_model: int, dropout: float = 0.1) -> None:
        super().__init__()
        assert d_model % h == 0
        self.d_k = d_model // h
        self.h = h
        self.linear_layers = nn.ModuleList([nn.Linear(d_model, d_model) for _ in range(3)])
        self.output_linear = nn.Linear(d_model, d_model)
        self.attention = Attention()
        self.dropout = nn.Dropout(p=dropout)

    def forward(self, query, key, value, mask=None):
        batch_size = query.size(0)
        query, key, value = [
            l(x).view(batch_size, -1, self.h, self.d_k).transpose(1, 2)
            for l, x in zip(self.linear_layers, (query, key, value))
        ]
        x, _ = self.attention(query, key, value, mask=mask, dropout=self.dropout)
        x = x.transpose(1, 2).contiguous().view(batch_size, -1, self.h * self.d_k)
        return self.output_linear(x)


class PositionwiseFeedForward(nn.Module):
    def __init__(self, d_model: int, d_ff: int) -> None:
        super().__init__()
        self.w_1 = nn.Linear(d_model, d_ff)
        self.w_2 = nn.Linear(d_ff, d_model)
        self.activation = GELU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.w_2(self.activation(self.w_1(x)))


class SublayerConnection(nn.Module):
    def __init__(self, size: int, dropout: float) -> None:
        super().__init__()
        self.layer_norm = LayerNorm(size)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x, sublayer):
        return self.layer_norm(x + self.dropout(sublayer(x)))


class TransformerBlock(nn.Module):
    def __init__(self, hidden: int, attn_heads: int, feed_forward_hidden: int, dropout: float) -> None:
        super().__init__()
        self.attention = MultiHeadedAttention(h=attn_heads, d_model=hidden, dropout=dropout)
        self.feed_forward = PositionwiseFeedForward(d_model=hidden, d_ff=feed_forward_hidden)
        self.input_sublayer = SublayerConnection(size=hidden, dropout=dropout)
        self.output_sublayer = SublayerConnection(size=hidden, dropout=dropout)
        self.dropout = nn.Dropout(p=dropout)

    def forward(self, x, mask):
        x = self.input_sublayer(x, lambda _x: self.attention.forward(_x, _x, _x, mask=mask))
        x = self.output_sublayer(x, self.feed_forward)
        return self.dropout(x)


# --------------------------------------------------------------------------- #
# The model
# --------------------------------------------------------------------------- #
@dataclass
class ModelArgs:
    """Matches the trained checkpoints. Defaults are the shipped config."""
    window_size: int = 480
    hidden: int = 256          # Discriminator hidden width (the inference network)
    heads: int = 2
    n_layers: int = 2
    output_size: int = 1
    drop_out: float = 0.1


class TransformerModel(nn.Module):
    def __init__(self, args: ModelArgs) -> None:
        super().__init__()
        self.original_len = args.window_size
        self.latent_len = int(self.original_len / 2)
        self.dropout_rate = args.drop_out
        self.hidden = args.hidden
        self.heads = args.heads
        self.n_layers = args.n_layers
        self.output_size = args.output_size

        self.conv = nn.Conv1d(1, self.hidden, kernel_size=5, stride=1, padding=2, padding_mode="replicate")
        self.pool = nn.LPPool1d(norm_type=2, kernel_size=2, stride=2)
        self.position = PositionalEmbedding(max_len=self.latent_len, d_model=self.hidden)
        self.layer_norm = LayerNorm(self.hidden)
        self.dropout = nn.Dropout(p=self.dropout_rate)
        self.transformer_blocks = nn.ModuleList(
            [TransformerBlock(self.hidden, self.heads, self.hidden * 4, self.dropout_rate) for _ in range(self.n_layers)]
        )
        self.deconv = nn.ConvTranspose1d(self.hidden, self.hidden, kernel_size=4, stride=2, padding=1)
        self.linear1 = nn.Linear(self.hidden, 128)
        self.linear2 = nn.Linear(128, self.output_size)

    def forward(self, sequence: torch.Tensor) -> torch.Tensor:
        x_token = self.pool(self.conv(sequence)).permute(0, 2, 1)
        embedding = x_token + self.position(sequence)
        x = self.dropout(self.layer_norm(embedding))
        for transformer in self.transformer_blocks:
            x = transformer.forward(x, None)
        x = self.deconv(x.permute(0, 2, 1)).permute(0, 2, 1)
        x = torch.tanh(self.linear1(x))
        x = self.linear2(x).permute(0, 2, 1)
        return x


class ELECTRICITY(nn.Module):
    """Full checkpoint container. At inference, the prediction is the Discriminator."""

    def __init__(self, args: ModelArgs) -> None:
        super().__init__()
        self.Discriminator = TransformerModel(args)
        gen_args = ModelArgs(**{**args.__dict__, "hidden": 64})
        self.Generator = TransformerModel(gen_args)

    def forward(self, sequence: torch.Tensor) -> torch.Tensor:
        # Inference path (pretrain=False): the Discriminator is the disaggregator.
        return self.Discriminator(sequence)


def load_electricity(checkpoint_path, device="cpu", args: ModelArgs | None = None) -> ELECTRICITY:
    """Load a shipped .pth into the faithful architecture (strict=True)."""
    args = args or ModelArgs()
    model = ELECTRICITY(args).to(device)
    state = torch.load(checkpoint_path, map_location=device)
    state = state.get("state_dict", state) if isinstance(state, dict) else state
    model.load_state_dict(state, strict=True)
    model.eval()
    return model
