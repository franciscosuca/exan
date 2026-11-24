"""Command line tools of the engine: ``exan-sidecar models list|download``.

The Windows installer runs ``exan-sidecar.exe models download <id> --select`` after the user picked a model
and agreed to the download; every progress line appears in the installer's detail list.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from .config import SettingsStore, desktop_data_dir, desktop_models_dir
from .downloads import DownloadError
from .engine.builtin_catalog import catalog, get_model
from .engine.model_store import ModelStore

_MESSAGES = {
    "en": {
        "start": "Downloading {label} ({size}) from {source}",
        "progress": "Downloading {label}: {percent}% ({done} of {size})",
        "done": "{label} is ready.",
        "failed": "The download of {label} failed: {error}",
        "unknown": "Unknown model: {model}. Known models: {known}",
        "cancelled": "Download cancelled; it continues where it stopped next time.",
    },
    "de": {
        "start": "{label} ({size}) wird von {source} heruntergeladen",
        "progress": "{label} wird heruntergeladen: {percent} % ({done} von {size})",
        "done": "{label} ist bereit.",
        "failed": "Der Download von {label} ist fehlgeschlagen: {error}",
        "unknown": "Unbekanntes Modell: {model}. Bekannte Modelle: {known}",
        "cancelled": "Download abgebrochen; er wird beim nächsten Mal fortgesetzt.",
    },
}


def _size(value: int) -> str:
    return f"{value / 1e9:.2f} GB" if value >= 1e9 else f"{value / 1e6:.0f} MB"


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    models = subparsers.add_parser("models", help="list or download the built-in models")
    actions = models.add_subparsers(dest="action", required=True)
    listing = actions.add_parser("list", help="show the built-in models")
    listing.add_argument("--json", action="store_true", help="machine-readable output")
    listing.add_argument("--models-dir", type=Path, default=None)
    download = actions.add_parser("download", help="download a built-in model (resumes partial downloads)")
    download.add_argument("model", help="model id, see `models list`")
    download.add_argument("--models-dir", type=Path, default=None, help="default: the desktop app's folder")
    download.add_argument("--data-dir", type=Path, default=None, help="settings folder for --select")
    download.add_argument("--select", action="store_true", help="use the model in the app afterwards")
    download.add_argument("--lang", choices=sorted(_MESSAGES), default="en")


def run(args: argparse.Namespace) -> int:
    store = ModelStore(args.models_dir or desktop_models_dir())
    if args.action == "list":
        rows = [{**m.view(), "installed": store.is_installed(m)} for m in catalog()]
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            for row in rows:
                flags = (" (recommended)" if row["recommended"] else "") + (
                    " [installed]" if row["installed"] else ""
                )
                print(f"{row['id']:24s} {_size(row['download_bytes']):>9s}  {row['label']}{flags}")
        return 0
    return _download(args, store)


def _download(args: argparse.Namespace, store: ModelStore) -> int:
    text = _MESSAGES[args.lang]
    model = get_model(args.model)
    if model is None:
        print(
            text["unknown"].format(model=args.model, known=", ".join(m.id for m in catalog())),
            file=sys.stderr,
        )
        return 2
    size = _size(model.download_bytes)
    print(text["start"].format(label=model.label, size=size, source="huggingface.co"), flush=True)
    last = {"percent": -1, "time": 0.0}

    def progress(status: str, done: int | None, total: int | None) -> None:
        if status != "downloading" or not total:
            return
        percent = int((done or 0) * 100 / total)
        now = time.monotonic()
        if percent >= last["percent"] + 5 or (percent > last["percent"] and now - last["time"] > 10):
            last.update(percent=percent, time=now)
            print(
                text["progress"].format(label=model.label, percent=percent, done=_size(done or 0), size=size),
                flush=True,
            )

    if args.select:
        # Saved first: if the download fails, the app still preselects this model and offers it again.
        SettingsStore((args.data_dir or desktop_data_dir()) / "settings.json").update(
            {"runtime": "builtin", "model": model.id}
        )
    try:
        asyncio.run(store.download(model, progress))
    except DownloadError as exc:
        print(text["failed"].format(label=model.label, error=exc.message), file=sys.stderr, flush=True)
        return 1
    except KeyboardInterrupt:
        print(text["cancelled"], file=sys.stderr)
        return 130
    print(text["done"].format(label=model.label), flush=True)
    return 0
