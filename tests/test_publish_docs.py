from pathlib import Path

from tools.publish_docs import publish_docs, _sanitize_slug


def _write_event_assets(data_root: Path, event_name: str, heatmap_name: str | None = None) -> None:
    event_dir = data_root / event_name
    html_dir = event_dir / "card_winrates_html"
    html_dir.mkdir(parents=True, exist_ok=True)
    (html_dir / "index.html").write_text(f"<html><body>{event_name}</body></html>", encoding="utf-8")
    (html_dir / "alpha.html").write_text("<html><body>alpha</body></html>", encoding="utf-8")

    heatmap_file = heatmap_name or f"{event_name} win matrix heatmap top15.png"
    (event_dir / heatmap_file).write_bytes(b"\x89PNG\r\n\x1a\nheatmap")


def test_publish_docs_full_rebuild_creates_event_pages(tmp_path):
    data_root = tmp_path / "data"
    docs_root = tmp_path / "docs"
    _write_event_assets(data_root, "PT Marvel 2026")
    _write_event_assets(data_root, "RC Houston 2025")

    publish_docs(data_root=data_root, docs_root=docs_root)

    marvel_slug = _sanitize_slug("PT Marvel 2026")
    houston_slug = _sanitize_slug("RC Houston 2025")

    root_index = (docs_root / "index.html").read_text(encoding="utf-8")
    marvel_page = (docs_root / marvel_slug / "index.html").read_text(encoding="utf-8")
    houston_page = (docs_root / houston_slug / "index.html").read_text(encoding="utf-8")

    assert "PT Marvel 2026" in root_index
    assert "RC Houston 2025" in root_index
    assert "card_winrates_html/index.html" in marvel_page
    assert "heatmaps/" in marvel_page
    assert (docs_root / marvel_slug / "card_winrates_html" / "index.html").exists()
    assert (docs_root / marvel_slug / "heatmaps" / "PT Marvel 2026 win matrix heatmap top15.png").exists()
    assert "card_winrates_html/index.html" in houston_page
    assert "heatmaps/" in houston_page


def test_publish_docs_selective_publish_preserves_existing_events(tmp_path):
    data_root = tmp_path / "data"
    docs_root = tmp_path / "docs"
    _write_event_assets(data_root, "PT Marvel 2026")
    _write_event_assets(data_root, "RC Houston 2025")

    publish_docs(data_root=data_root, docs_root=docs_root)

    _write_event_assets(data_root, "RC Australia 2025")
    publish_docs(["RC Australia 2025"], data_root=data_root, docs_root=docs_root)

    root_index = (docs_root / "index.html").read_text(encoding="utf-8")
    assert "PT Marvel 2026" in root_index
    assert "RC Houston 2025" in root_index
    assert "RC Australia 2025" in root_index

    australia_slug = _sanitize_slug("RC Australia 2025")
    assert (docs_root / australia_slug / "index.html").exists()
    assert (docs_root / australia_slug / "card_winrates_html" / "index.html").exists()
    assert (docs_root / australia_slug / "heatmaps" / "RC Australia 2025 win matrix heatmap top15.png").exists()