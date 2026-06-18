from pathlib import Path

import camac_core


def solve() -> None:
    project_root = Path(__file__).resolve().parents[1]
    file_path = project_root / "sample_data" / "190723.001"

    archive = camac_core.parse_camac_file(str(file_path))

    print("Event count:", archive.event_count())
    print("First 5 relative seconds:", archive.relative_seconds()[:5])
    print("First 5 AE max abs:", archive.ae_max_abs_values()[:5])
    print("Event 0 info:", archive.event_info(0))
    print("Event 0 AE signal length:", len(archive.ae_signal(0)))
    print("Event 0 EME signal length:", len(archive.eme_signal(0)))


if __name__ == "__main__":
    solve()
