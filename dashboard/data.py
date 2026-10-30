"""Cached, read-only access to the validated processed data.

The dashboard calls the same analytics functions as the FastAPI backend (backend/app/*),
so every number on screen has one implementation. No database is needed.
"""
from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from backend.app import analytics, insights, nlq, simulator
from backend.app.store import DataStore
from backend.pipeline.paths import METADATA_DIR, PROCESSED_DIR
from backend.pipeline.quality import missingness_summary

THEME_LABELS = {
    "monetary_poverty": "Monetary poverty", "multidimensional_poverty": "Multidimensional poverty",
    "mpi_indicator": "MPI indicators", "financial_inclusion": "Financial inclusion", "social_protection": "Social protection",
    "basic_services": "Basic services", "housing": "Housing", "health": "Health", "digital": "Digital access",
    "labour": "Labour", "transfers": "Transfers", "demography": "Demography", "resilience": "Resilience",
}
LEVEL_LABELS = {"national": "National", "area": "Urban / rural", "province": "Province", "district": "District",
                "quintile": "Consumption quintile", "sex": "Sex", "sex_of_head": "Sex of household head",
                "poverty_status": "Poverty status", "k_value": "MPI cut-off k", "vup_component": "VUP component",
                "age_group": "Age group", "type_of_habitat": "Type of habitat", "disability_status": "Disability status",
                "vup_all": "VUP (all)"}


class DataUnavailable(RuntimeError):
    pass


@st.cache_resource(show_spinner="Loading validated NISR datasets…")
def store() -> DataStore:
    try:
        return DataStore(PROCESSED_DIR)
    except FileNotFoundError as exc:
        raise DataUnavailable(str(exc)) from exc


@st.cache_data(show_spinner=False)
def dashboard() -> dict:
    return analytics.dashboard(store())


@st.cache_data(show_spinner=False)
def mpi() -> dict:
    return analytics.mpi_summary(store())


@st.cache_data(show_spinner=False)
def financial() -> dict:
    return analytics.financial_inclusion(store())


@st.cache_data(show_spinner=False)
def trends() -> dict:
    return analytics.trends(store())


@st.cache_data(show_spinner=False)
def quality() -> dict:
    return analytics.data_quality(store())


@st.cache_data(show_spinner=False)
def policy_insights() -> dict:
    return insights.policy_insights(store())


@st.cache_data(show_spinner="Computing rank intervals…")
def map_layer(indicator: str, level: str) -> dict:
    return analytics.map_layer(store(), indicator, level)


@st.cache_data(show_spinner=False)
def profile(level: str, geo_id: str) -> dict:
    return analytics.profile(store(), level, geo_id)


@st.cache_data(show_spinner=False)
def correlations(indicators: tuple[str, ...] | None = None, level: str = "district") -> dict:
    return analytics.correlations(store(), list(indicators) if indicators else None, level)


@st.cache_data(show_spinner=False)
def composite() -> dict:
    return analytics.composite_index(store())


@st.cache_data(show_spinner=False)
def sim_context(level: str, geo_id: str) -> dict:
    return simulator.context(store(), level, geo_id)


def ask(question: str) -> dict:
    return nlq.ask(store(), question)


@st.cache_data(show_spinner=False)
def observations_df() -> pd.DataFrame:
    df = pd.DataFrame(store().observations)
    meta = pd.DataFrame(store().indicators)[["id", "name", "theme", "unit", "universe"]].rename(
        columns={"id": "indicator_id", "name": "indicator_name"})
    return df.merge(meta, on="indicator_id", how="left")


@st.cache_data(show_spinner=False)
def indicators_df() -> pd.DataFrame:
    df = pd.DataFrame(store().indicators)
    df["levels"] = df["levels"].apply(lambda v: ", ".join(v))
    return df


@st.cache_data(show_spinner=False)
def sources_df() -> pd.DataFrame:
    rows = []
    for s in store().sources:
        r = s.get("retrieval") or {}
        rows.append({k: s.get(k) for k in ("id", "short", "title", "publisher", "period", "format", "access", "license",
                                           "used_for", "url", "landing_page", "citation")} |
                    {"retrieved_at": r.get("retrieved_at"), "sha256": r.get("sha256"), "bytes": r.get("bytes")})
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def missingness_df() -> pd.DataFrame:
    return pd.DataFrame(missingness_summary(store().observations))


@st.cache_data(show_spinner=False)
def inventory() -> list[dict]:
    """Data inventory written by the pipeline (raw files are not deployed, so this is the build-time record)."""
    p = METADATA_DIR / "data_inventory.json"
    return json.loads(p.read_text("utf-8")) if p.exists() else []


def name_of(level: str, geo_id: str) -> str:
    return store().geo_name(level, geo_id) or geo_id


def district_options() -> list[tuple[str, str]]:
    return sorted(((d["geo_id"], d["name"]) for d in store().districts()), key=lambda x: x[1])


def province_options() -> list[tuple[str, str]]:
    return [(p["geo_id"], p["name"]) for p in store().provinces()]


def indicator_meta(ind: str) -> dict:
    return store().indicator_index.get(ind, {})
