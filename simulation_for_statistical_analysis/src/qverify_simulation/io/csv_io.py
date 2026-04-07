"""CSV persistence for experiment distributions.

Each distribution is stored as a two-column CSV (value, probability).
Three files are written per experiment run:
  err_eb.csv, err_imr.csv, err_v1.csv
"""

import csv
from pathlib import Path

_NAMES = ("err_eb", "err_imr", "err_v1")


def _write(path: Path, dist: dict[float, float]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["value", "probability"])
        for k, v in sorted(dist.items()):
            writer.writerow([k, v])


def _read(path: Path) -> dict[float, float]:
    dist: dict[float, float] = {}
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            dist[float(row["value"])] = float(row["probability"])
    return dist


def save_distributions(
    output_dir: str | Path,
    err_eb: dict[float, float],
    err_imr: dict[float, float],
    err_v1: dict[float, float],
) -> None:
    """Save all three distributions to CSV files in *output_dir*."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, dist in zip(_NAMES, (err_eb, err_imr, err_v1)):
        _write(out / f"{name}.csv", dist)


def load_distributions(
    data_dir: str | Path,
) -> tuple[dict[float, float], dict[float, float], dict[float, float]]:
    """Load distributions from CSVs in *data_dir*.

    Returns:
        (err_eb, err_imr, err_v1)
    """
    d = Path(data_dir)
    missing = [n for n in _NAMES if not (d / f"{n}.csv").exists()]
    if missing:
        raise FileNotFoundError(
            f"Missing CSV files in {d}: {', '.join(f'{n}.csv' for n in missing)}"
        )
    return tuple(_read(d / f"{name}.csv") for name in _NAMES)  # type: ignore[return-value]
