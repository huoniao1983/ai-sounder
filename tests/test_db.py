from sqlalchemy import inspect

from engine.db.init_db import init_schema


def test_schema_creates_prd_tables_in_memory() -> None:
    engine = init_schema("sqlite:///:memory:")
    tables = set(inspect(engine).get_table_names())
    assert {
        "live_presets",
        "script_groups",
        "scripts",
        "music_playlists",
        "music_tracks",
        "playback_history",
        "voice_profiles",
        "leads",
        "stored_credentials",
    }.issubset(tables)

