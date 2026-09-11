"""SQLAlchemy models following the PRD v2.0 schema."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ScriptGroup(Base):
    __tablename__ = "script_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    platform: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    scripts: Mapped[list["Script"]] = relationship(
        back_populates="group",
        cascade="all, delete-orphan",
    )


class Script(Base):
    __tablename__ = "scripts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("script_groups.id"), index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    group: Mapped[ScriptGroup] = relationship(back_populates="scripts")


class MusicPlaylist(Base):
    __tablename__ = "music_playlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    license_note: Mapped[str | None] = mapped_column(Text)

    tracks: Mapped[list["MusicTrack"]] = relationship(
        back_populates="playlist",
        cascade="all, delete-orphan",
    )


class MusicTrack(Base):
    __tablename__ = "music_tracks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    playlist_id: Mapped[int] = mapped_column(ForeignKey("music_playlists.id"), index=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    title: Mapped[str | None] = mapped_column(String(200))
    duration_sec: Mapped[int | None] = mapped_column(Integer)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    playlist: Mapped[MusicPlaylist] = relationship(back_populates="tracks")


class LivePreset(Base):
    __tablename__ = "live_presets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    preset_name: Mapped[str] = mapped_column(String(200), nullable=False)
    voice_id: Mapped[str] = mapped_column(String(100), nullable=False)
    tts_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    script_group_id: Mapped[int | None] = mapped_column(
        ForeignKey("script_groups.id"),
    )
    music_playlist_id: Mapped[int | None] = mapped_column(
        ForeignKey("music_playlists.id"),
    )
    shuffle_mode: Mapped[str] = mapped_column(String(20), default="weighted_random")
    min_gap_seconds: Mapped[float] = mapped_column(Float, default=3.0)
    max_gap_seconds: Mapped[float] = mapped_column(Float, default=8.0)
    interrupt_mode: Mapped[str] = mapped_column(String(20), default="queue")
    bgm_volume: Mapped[float] = mapped_column(Float, default=0.35)
    ducking_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime)


class PlaybackHistory(Base):
    __tablename__ = "playback_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int | None] = mapped_column(Integer, index=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    ref_id: Mapped[str | None] = mapped_column(String(100))
    content_snapshot: Mapped[str] = mapped_column(Text)
    played_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    cycle_no: Mapped[int | None] = mapped_column(Integer)
    queue_pos: Mapped[int | None] = mapped_column(Integer)


class VoiceProfile(Base):
    __tablename__ = "voice_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    voice_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(30), default="preset")
    sample_path: Mapped[str | None] = mapped_column(String(500))
    is_preset: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(String(30), nullable=False)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    nickname: Mapped[str] = mapped_column(String(200))
    event_type: Mapped[str] = mapped_column(String(20))
    score: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[str] = mapped_column(String(20))
    wechat: Mapped[str | None] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(50))
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class StoredCredential(Base):
    __tablename__ = "stored_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    account: Mapped[str] = mapped_column(String(200))
    encrypted_payload: Mapped[bytes] = mapped_column(nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

