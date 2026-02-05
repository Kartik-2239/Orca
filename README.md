# Video Downloader (made by codex)

PySide6 app that downloads videos with `yt-dlp` + `ffmpeg` and previews them inside the UI.

## Requirements

- Python 3.12+
- `yt-dlp` installed and on your PATH
- `ffmpeg` installed and on your PATH
- `PySide6` installed

## Run

```bash
python main.py
```

## Build (macOS)

```bash
pyinstaller --noconfirm --windowed --name "VideoDownloader" \
  --add-binary "/path/to/yt-dlp:." \
  --add-binary "/path/to/ffmpeg:." \
  --add-binary "/path/to/ffprobe:." \
  main.py
```

**Note:** Change `/opt/homebrew/bin/` to your actual path where `yt-dlp`, `ffmpeg`, and `ffprobe` are installed.

## Notes

- Downloads are saved into `./downloads` by default.
- Use **Open Video** to test playback with an existing file.

## Possible Things To Add

1. Embed metadata
2. Embed thumbnail
3. Write thumbnail file
4. Write subtitle files
5. Subtitle language(s)
6. Limit download speed
7. Max retries
8. Socket timeout
9. Proxy
10. Cookies file
11. User-agent override
12. Convert/recode output (mp4/mkv/mp3)
13. Extract audio + bitrate
14. Trim by time range (start/end)
