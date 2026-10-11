from __future__ import annotations

import datetime as dt

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Source(Base):
    __tablename__ = "sources"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    publisher: Mapped[str] = mapped_column(String(300))
    url: Mapped[str] = mapped_column(String(500))
    period: Mapped[str | None] = mapped_column(String(100))
    access: Mapped[str | None] = mapped_column(String(200))
    sha256: Mapped[str | None] = mapped_column(String(64))
    retrieved_at: Mapped[str | None] = mapped_column(String(20))
    citation: Mapped[str | None] = mapped_column(Text)


class Indicator(Base):
    __tablename__ = "indicators"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(300))
    theme: Mapped[str] = mapped_column(String(60))
    unit: Mapped[str] = mapped_column(String(60))
    universe: Mapped[str | None] = mapped_column(String(120))
    definition: Mapped[str] = mapped_column(Text)
    period: Mapped[str] = mapped_column(String(60))
    source_id: Mapped[str] = mapped_column(String(64))
    table_ref: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(40))


class Observation(Base):
    __tablename__ = "observations"
    __table_args__ = (UniqueConstraint("indicator_id", "level", "geo_id", "period", "breakdown", name="uq_obs"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    indicator_id: Mapped[str] = mapped_column(String(80), index=True)
    level: Mapped[str] = mapped_column(String(40), index=True)
    geo_id: Mapped[str] = mapped_column(String(60))
    geo_name: Mapped[str] = mapped_column(String(120))
    period: Mapped[str] = mapped_column(String(40))
    breakdown: Mapped[str] = mapped_column(String(120), default="")
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    se: Mapped[float | None] = mapped_column(Float, nullable=True)
    ci_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    ci_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    cv: Mapped[float | None] = mapped_column(Float, nullable=True)
    deff: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(40))
    source_id: Mapped[str] = mapped_column(String(64))
    table_ref: Mapped[str] = mapped_column(String(120))
    flags: Mapped[str] = mapped_column(String(400), default="")


class Scenario(Base):
    __tablename__ = "scenarios"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=lambda: dt.datetime.now(dt.timezone.utc).replace(tzinfo=None))
    inputs: Mapped[dict] = mapped_column(JSON)
    summary: Mapped[dict] = mapped_column(JSON)
    # SHA-256 of a random token returned once to the creator; required to delete the scenario.
    delete_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
