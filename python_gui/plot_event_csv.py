import sys
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


def plot_signal(csv_path: Path, title: str) -> None:
    data = pd.read_csv(csv_path)

    plt.figure(figsize=(12, 5))
    plt.plot(data["time_microseconds"], data["signal_value"])
    plt.title(title)
    plt.xlabel("Time, microseconds")
    plt.ylabel("Signal value, ADC counts from mean")
    plt.grid(True)
    plt.show()


def solve() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 python_gui/plot_event_csv.py <event_index>")
        return

    event_index = sys.argv[1]

    project_root = Path(__file__).resolve().parents[1]
    exports_dir = project_root / "exports"

    ae_path = exports_dir / f"event_{event_index}_ae_signal.csv"
    eme_path = exports_dir / f"event_{event_index}_eme_signal.csv"

    if not ae_path.exists():
        print(f"Missing file: {ae_path}")
        return

    if not eme_path.exists():
        print(f"Missing file: {eme_path}")
        return

    plot_signal(ae_path, f"Event {event_index} AE Signal")
    plot_signal(eme_path, f"Event {event_index} EME Signal")


if __name__ == "__main__":
    solve()
