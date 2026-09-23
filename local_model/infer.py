"""
infer.py — Local inference for Bangla Transliteration model
============================================================
Loads a fine-tuned TinyTransliterator and runs interactive / batch transliteration.

Usage:
  # Interactive mode (Roman → Bangla)
  python infer.py --model model/ro2bn_ft

  # Batch mode from stdin
  echo "ami tomake bhalobashi" | python infer.py --model model/ro2bn_ft --batch

  # Evaluate CER on a CSV file
  python infer.py --model model/ro2bn_ft --eval data/tier1_gold_test.csv

  # Reverse (Bangla → Roman)
  python infer.py --model model/bn2ro_ft --reverse
"""

import argparse
import csv
import json
import math
import sys
import unicodedata
from pathlib import Path

import torch
import torch.nn as nn

# ── constants ─────────────────────────────────────────────────────────────────
PAD, SOS, EOS, UNK = 0, 1, 2, 3


# ── minimal model definitions (no dependency on train.py) ─────────────────────

class Vocab:
    @classmethod
    def load(cls, path):
        v = cls()
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        v.c2i = d["c2i"]
        v.i2c = {int(k): val for k, val in d["i2c"].items()}
        return v

    def encode(self, text, maxlen=None):
        """Encode source text: no SOS, with EOS (matches training TlitDataset)."""
        ids = [self.c2i.get(c, UNK) for c in text]
        if maxlen:
            ids = ids[:maxlen]
        return ids + [EOS]

    def decode(self, ids):
        out = []
        for i in ids:
            if i == EOS:
                break
            if i in (PAD, SOS):
                continue
            out.append(self.i2c.get(i, "?"))
        return "".join(out)

    def __len__(self):
        return len(self.c2i)


class SinPE(nn.Module):
    def __init__(self, d_model, maxlen=512, dropout=0.0):
        super().__init__()
        self.drop = nn.Dropout(dropout)
        buf_len = max(maxlen * 2, 1024)
        pe  = torch.zeros(buf_len, d_model)
        pos = torch.arange(0, buf_len).unsqueeze(1).float()
        div = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(pos * div)
        pe[:, 1::2] = torch.cos(pos * div)
        self.register_buffer("pe", pe.unsqueeze(0))

    def forward(self, x):
        return self.drop(x + self.pe[:, :x.size(1)])


class TinyTransliterator(nn.Module):
    def __init__(self, src_vsz, tgt_vsz, d=128, nhead=4,
                 enc_layers=3, dec_layers=3, ffn=256, dropout=0.0, maxlen=256):
        super().__init__()
        self.src_emb = nn.Embedding(src_vsz, d, padding_idx=PAD)
        self.tgt_emb = nn.Embedding(tgt_vsz, d, padding_idx=PAD)
        self.pe      = SinPE(d, maxlen, dropout)
        self.tf      = nn.Transformer(
            d_model=d, nhead=nhead,
            num_encoder_layers=enc_layers, num_decoder_layers=dec_layers,
            dim_feedforward=ffn, dropout=dropout, batch_first=True,
        )
        self.proj = nn.Linear(d, tgt_vsz)

    @torch.no_grad()
    def greedy(self, src_ids, tgt_vocab, device, maxlen=256):
        self.eval()
        src     = src_ids.unsqueeze(0).to(device)
        src_pad = (src == PAD)
        mem     = self.tf.encoder(self.pe(self.src_emb(src)), src_key_padding_mask=src_pad)
        out_ids = [SOS]
        for _ in range(maxlen):
            tgt    = torch.tensor(out_ids, dtype=torch.long, device=device).unsqueeze(0)
            te     = self.pe(self.tgt_emb(tgt))
            tmask  = nn.Transformer.generate_square_subsequent_mask(len(out_ids), device=device)
            dec    = self.tf.decoder(te, mem, tgt_mask=tmask)
            nxt    = self.proj(dec[:, -1]).argmax(-1).item()
            if nxt == EOS:
                break
            out_ids.append(nxt)
        return tgt_vocab.decode(out_ids[1:])


# ── helpers ───────────────────────────────────────────────────────────────────

def load_model(model_dir, device="cpu"):
    d = Path(model_dir)
    cfg      = json.load(open(d / "config.json"))
    src_v    = Vocab.load(d / "src_vocab.json")
    tgt_v    = Vocab.load(d / "tgt_vocab.json")
    model    = TinyTransliterator(
        src_vsz=len(src_v), tgt_vsz=len(tgt_v),
        d=cfg["d_model"], nhead=cfg["nhead"],
        enc_layers=cfg["layers"], dec_layers=cfg["layers"],
        ffn=cfg["ffn"], maxlen=cfg["maxlen"],
    )
    state = torch.load(d / "best_model.pt", map_location=device, weights_only=False)
    model.load_state_dict(state)
    model.to(device)
    model.eval()
    return model, src_v, tgt_v, cfg


def transliterate(text, model, src_v, tgt_v, device, cfg, reverse=False):
    text = unicodedata.normalize("NFC", text.strip())
    if reverse:
        src_v, tgt_v = tgt_v, src_v
    maxlen = cfg["maxlen"]
    src_ids = torch.tensor(src_v.encode(text, maxlen=maxlen - 2), dtype=torch.long)
    return model.greedy(src_ids, tgt_v, device, maxlen)


def cer(pred, ref):
    """Character error rate via dynamic programming (no external deps)."""
    if not ref:
        return 0.0
    m, n = len(pred), len(ref)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, n + 1):
            temp = dp[j]
            if pred[i - 1] == ref[j - 1]:
                dp[j] = prev
            else:
                dp[j] = 1 + min(prev, dp[j], dp[j - 1])
            prev = temp
    return dp[n] / n


# ── main ──────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--model",   default="model/ro2bn_ft", help="Model directory")
    p.add_argument("--eval",    default=None, help="CSV file for CER evaluation")
    p.add_argument("--batch",   action="store_true", help="Read lines from stdin")
    p.add_argument("--reverse", action="store_true", help="Bangla→Roman direction")
    p.add_argument("--device",  default="cpu", help="cpu or cuda")
    return p.parse_args()


def main():
    args = parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    print(f"Loading model from {args.model}...", file=sys.stderr)
    model, src_v, tgt_v, cfg = load_model(args.model, args.device)
    direction = "Bangla→Roman" if args.reverse else "Roman→Bangla"
    print(f"Model loaded ({sum(p.numel() for p in model.parameters()):,} params, {direction})\n",
          file=sys.stderr)

    # ── evaluation mode ───────────────────────────────────────────────────────
    if args.eval:
        pairs = []
        with open(args.eval, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                roman  = unicodedata.normalize("NFC", row["roman"].strip())
                bangla = unicodedata.normalize("NFC", row["bangla"].strip())
                if roman and bangla:
                    pairs.append((roman, bangla))

        total_dist, total_len, n_perfect = 0, 0, 0
        wrong_samples = []
        for roman, bangla in pairs:
            src_text = bangla if args.reverse else roman
            ref_text = roman  if args.reverse else bangla
            pred = transliterate(src_text, model, src_v, tgt_v, args.device, cfg, args.reverse)
            d    = sum(1 for a, b in zip(pred, ref_text) if a != b) + abs(len(pred) - len(ref_text))
            ed   = int(round(cer(pred, ref_text) * len(ref_text)))
            total_dist += ed
            total_len  += len(ref_text)
            if pred == ref_text:
                n_perfect += 1
            else:
                wrong_samples.append((src_text, pred, ref_text))

        overall_cer = total_dist / max(total_len, 1) * 100
        pct_perfect = n_perfect / len(pairs) * 100
        print(f"Evaluated {len(pairs)} pairs")
        print(f"CER          : {overall_cer:.2f}%")
        print(f"Perfect match: {n_perfect}/{len(pairs)} ({pct_perfect:.1f}%)")
        print(f"\n--- Sample errors (first 20) ---")
        for src, pred, ref in wrong_samples[:20]:
            print(f"  IN : {src[:60]}")
            print(f"  OUT: {pred[:60]}")
            print(f"  REF: {ref[:60]}")
            print()
        return

    # ── batch stdin mode ──────────────────────────────────────────────────────
    if args.batch:
        for line in sys.stdin:
            line = line.rstrip("\n")
            if not line:
                print("")
                continue
            pred = transliterate(line, model, src_v, tgt_v, args.device, cfg, args.reverse)
            print(pred)
        return

    # ── interactive mode ──────────────────────────────────────────────────────
    src_lang = "Bangla" if args.reverse else "Roman"
    tgt_lang = "Roman" if args.reverse else "Bangla"
    print(f"Interactive mode: type {src_lang} text, get {tgt_lang} output.")
    print("Press Ctrl+C or Ctrl+D to exit.\n")
    try:
        while True:
            try:
                text = input(f"{src_lang}> ")
            except EOFError:
                break
            if not text.strip():
                continue
            pred = transliterate(text, model, src_v, tgt_v, args.device, cfg, args.reverse)
            print(f"{tgt_lang}> {pred}\n")
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
