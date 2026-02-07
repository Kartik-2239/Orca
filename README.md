# Orca (made by codex)

PySide6 app that downloads videos with `yt-dlp` + `ffmpeg` and previews them inside the UI.

## Requirements

- Python 3.12+
- `yt-dlp` installed and on your PATH
- `ffmpeg` installed and on your PATH
- `PySide6` installed
- `PyMuPDF` installed

## Run

```bash
python main.py
```

## Build (macOS)

Make sure all runtime dependencies are installed in the same Python environment you run `pyinstaller` from
(PySide6, PyMuPDF, requests, beautifulsoup4, pillow).

```bash
pyinstaller --noconfirm --windowed --name "Orca" \
  --add-binary "/path/to/yt-dlp:." \
  --add-binary "/path/to/ffmpeg:." \
  --add-binary "/path/to/ffprobe:." \
  main.py
```

**Note:** Replace `/path/to/...` with the actual paths from `which yt-dlp`, `which ffmpeg`, and `which ffprobe`.

## Notes

- Downloads are saved into `./downloads` by default.
- Use **Open Video** to test playback with an existing file.

## Possible Things To Add

See `TODO.md`.
