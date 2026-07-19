from pathlib import Path

from scripts.create_card_winrates import create_all_card_winrates


def _write_minimal_decklists(event_dir: Path, event_name: str) -> None:
    content = "\n".join(
        [
            "player,deck_archetype,card_name,qty,zone,wins,losses",
            "Alice,Archetype One,Card A,4,main,3,1",
            "Alice,Archetype One,Card B,2,side,3,1",
            "Bob,Archetype One,Card A,0,main,1,3",
            "Bob,Archetype One,Card B,1,side,1,3",
            "Cara,Archetype Two,Card C,3,main,2,2",
            "Cara,Archetype Two,Card D,1,side,2,2",
            "Dan,Archetype Two,Card C,0,main,0,4",
            "Dan,Archetype Two,Card D,2,side,0,4",
        ]
    )
    (event_dir / f"{event_name} decklists.csv").write_text(content, encoding="utf-8")


def test_card_winrates_generates_csv_and_html_by_default(tmp_path, monkeypatch):
    event_name = "Unit Test Event"
    event_dir = tmp_path / event_name
    event_dir.mkdir(parents=True)
    _write_minimal_decklists(event_dir, event_name)

    monkeypatch.setenv("EVENT_DATA_DIR", str(event_dir))
    monkeypatch.setenv("EVENT_NAME", event_name)
    monkeypatch.delenv("CARD_WINRATES_HTML", raising=False)
    monkeypatch.delenv("CARD_WINRATES_OPEN_HTML", raising=False)

    written = create_all_card_winrates()

    assert written
    assert (event_dir / "card_winrates").exists()
    assert (event_dir / "card_winrates_html" / "index.html").exists()

    html_files = list((event_dir / "card_winrates_html").glob("*.html"))
    # Index + per-archetype pages.
    assert len(html_files) >= 3



def test_card_winrates_can_disable_html_without_affecting_csv(tmp_path, monkeypatch):
    event_name = "Unit Test Event"
    event_dir = tmp_path / event_name
    event_dir.mkdir(parents=True)
    _write_minimal_decklists(event_dir, event_name)

    monkeypatch.setenv("EVENT_DATA_DIR", str(event_dir))
    monkeypatch.setenv("EVENT_NAME", event_name)
    monkeypatch.setenv("CARD_WINRATES_HTML", "0")

    written = create_all_card_winrates()

    assert written
    assert (event_dir / "card_winrates").exists()
    assert not (event_dir / "card_winrates_html" / "index.html").exists()
