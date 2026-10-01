import subprocess
import tempfile
from pathlib import Path

SUPPORTED_TARGETS = {"docx", "xlsx", "txt", "csv", "pptx", "pdf"}


def convert_document(source_path, target_format):
    """Runs LibreOffice headless, any source office/PDF format to any of
    SUPPORTED_TARGETS, best-effort (LibreOffice decides what it can import
    from the source and how to lay it out in the target — e.g. pptx→xlsx
    is unusual but not blocked). Returns the result file's bytes.
    """
    target_format = target_format.lower()
    if target_format not in SUPPORTED_TARGETS:
        raise ValueError(f"Unsupported target format: {target_format}")

    with tempfile.TemporaryDirectory() as tmp_dir, tempfile.TemporaryDirectory() as profile_dir:
        cmd = [
            "soffice",
            "--headless",
            "--norestore",
            f"-env:UserInstallation=file://{profile_dir}",
            "--convert-to", target_format,
            "--outdir", tmp_dir,
            source_path,
        ]
        subprocess.run(cmd, capture_output=True, check=True, timeout=300)

        produced = list(Path(tmp_dir).glob(f"*.{target_format}"))
        if not produced:
            raise RuntimeError("LibreOffice did not produce an output file for this conversion.")
        return produced[0].read_bytes()
