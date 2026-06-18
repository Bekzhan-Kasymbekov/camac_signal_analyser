from pathlib import Path
from typing import Optional


class app_state:
    def __init__(self) -> None:
        self.archive = None
        self.file_path: Optional[Path] = None
        self.encoding_format: str = "old_ae_header"

    def has_archive(self) -> bool:
        return self.archive is not None
