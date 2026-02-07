# Memories

## PDF Editor Tabs (Hidden For Now)

The PDF editor still uses `QTabWidget`, but the tab bar is hidden to remove the tab display.

- Hide tabs: `/Users/kartikkannan/Desktop/File/Video-downloader/ui/pdf_editor_page.py` in `_build_ui()`:
  - `self.tabs.tabBar().hide()`
- To re-enable tabs later:
  - Replace with `self.tabs.tabBar().show()` or remove the `hide()` call.
  - Optional: `self.tabs.setTabsClosable(True)` already wired to close.

## Export Area (White Background + Dim Overlay)

The image editor renders a white export canvas and dims the non-export area.  
Key code locations:

- Export overlay creation + update:
  - `/Users/kartikkannan/Desktop/File/Video-downloader/ui/image_editor_page.py` in `_ensure_export_overlay()` and `_update_export_overlay()`.
  - The white background is a `QGraphicsRectItem` (`self._export_bg_item`).
  - The dimmed mask is a `QGraphicsPathItem` (`self._export_mask_item`) using an odd-even fill.

- Export rectangle source (locked to original size):
  - `/Users/kartikkannan/Desktop/File/Video-downloader/ui/image_editor_page.py` in `_export_rect()`.
  - It uses `_export_base_rect` + `_export_base_size` (set in `_set_base_image()` and updated in `_on_base_size_changed()`).
  - The export area stays tied to the *original image size* and does not change when the base layer is scaled/moved.

- Export render logic:
  - `/Users/kartikkannan/Desktop/File/Video-downloader/ui/image_editor_page.py` in `_render_scene()` which renders only the export rect into the final image.
