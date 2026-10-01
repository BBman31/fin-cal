"""Plotly figure builders.

Colors follow the dataviz reference palette: buckets take categorical slots 1-3 in fixed
order (validated all-pairs, light + dark), Unmapped is neutral gray, and "over budget"
uses the reserved critical status color together with a text label.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import plotly.graph_objects as go

from fincal.mapping import UNMAPPED
from fincal.models import BUCKETS


@dataclass(frozen=True)
class Theme:
    surface: str
    ink: str
    ink_secondary: str
    muted: str
    grid: str
    baseline: str
    track: str
    buckets: dict[str, str]
    critical: str = "#d03b3b"


LIGHT = Theme(
    surface="#fcfcfb",
    ink="#0b0b0b",
    ink_secondary="#52514e",
    muted="#898781",
    grid="#e1e0d9",
    baseline="#c3c2b7",
    track="#f0efec",
    buckets={"Fixed": "#2a78d6", "Future": "#eb6834", "Flexible": "#1baf7a", UNMAPPED: "#898781"},
)
DARK = Theme(
    surface="#1a1a19",
    ink="#ffffff",
    ink_secondary="#c3c2b7",
    muted="#898781",
    grid="#2c2c2a",
    baseline="#383835",
    track="#383835",
    buckets={"Fixed": "#3987e5", "Future": "#d95926", "Flexible": "#199e70", UNMAPPED: "#898781"},
)

BAR_RADIUS = 4
FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'


def theme(dark: bool) -> Theme:
    return DARK if dark else LIGHT


def _layout(fig: go.Figure, t: Theme, height: int, currency: str, **kwargs) -> go.Figure:
    fig.update_layout(
        height=height,
        margin={"l": 8, "r": 8, "t": 8, "b": 8},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": FONT, "color": t.ink_secondary, "size": 13},
        hoverlabel={"bgcolor": t.surface, "font": {"color": t.ink, "family": FONT}},
        legend={"orientation": "h", "y": 1.02, "yanchor": "bottom", "x": 0, "title": None},
        separators=". ",
        **{"bargap": 0.35, **kwargs},
    )
    axis = {
        "gridcolor": t.grid,
        "gridwidth": 1,
        "zerolinecolor": t.baseline,
        "linecolor": t.baseline,
        "tickfont": {"color": t.muted},
        "title": None,
    }
    fig.update_xaxes(**axis)
    fig.update_yaxes(**axis)
    return fig


def plan_vs_actual(
    df: pd.DataFrame, label: str, t: Theme, currency: str, color: str | None = None
) -> go.Figure:
    """Bullet chart: a pale track = budget, a solid bar = actual, over-budget bars in red.

    ``df`` has columns [label, budget, actual]; ``color`` defaults to the bucket color when
    ``label == "bucket"``.
    """
    df = df.iloc[::-1]  # plotly draws bottom-up; keep the table order top-down
    names = df[label].astype(str).tolist()
    over = (df["actual"] > df["budget"]) & (df["budget"] > 0)
    unbudgeted = df["budget"] <= 0
    if color is None:
        colors = [t.buckets.get(n, t.muted) for n in names]
    else:
        colors = [color] * len(df)
    colors = [
        t.critical if o else t.muted if u else c
        for c, o, u in zip(colors, over, unbudgeted, strict=True)
    ]

    fig = go.Figure()
    fig.add_bar(
        y=names,
        x=df["budget"],
        orientation="h",
        marker={"color": t.track, "cornerradius": BAR_RADIUS},
        width=0.7,
        name="Budget",
        hovertemplate=f"%{{y}}<br>Budget %{{x:,.0f}} {currency}<extra></extra>",
    )
    texts = []
    for a, b, o in zip(df["actual"], df["budget"], over, strict=True):
        if b <= 0:
            texts.append(f"{a:,.0f}  · no budget".replace(",", " "))
        elif o:
            texts.append(f"{a:,.0f}  ▲ over by {a - b:,.0f}".replace(",", " "))
        else:
            texts.append(f"{a:,.0f}  · {a / b:.0%}".replace(",", " "))
    fig.add_bar(
        y=names,
        x=df["actual"],
        orientation="h",
        marker={"color": colors, "cornerradius": BAR_RADIUS},
        width=0.32,
        name="Actual",
        customdata=df[["budget", "remaining"]].to_numpy(),
        hovertemplate=(
            f"%{{y}}<br>Spent %{{x:,.0f}} {currency}"
            f"<br>Budget %{{customdata[0]:,.0f}} {currency}"
            f"<br>Remaining %{{customdata[1]:,.0f}} {currency}<extra></extra>"
        ),
    )
    for name, text, a, b in zip(names, texts, df["actual"], df["budget"], strict=True):
        fig.add_annotation(
            x=max(a, b),
            y=name,
            text=text,
            showarrow=False,
            xanchor="left",
            xshift=6,
            font={"color": t.ink_secondary, "size": 12},
        )
    xmax = float(max(df["budget"].max(), df["actual"].max(), 1)) * 1.45
    _layout(
        fig,
        t,
        height=max(140, 46 * len(df) + 40),
        currency=currency,
        barmode="overlay",
        showlegend=False,
    )
    fig.update_xaxes(range=[0, xmax], showgrid=True, ticksuffix="")
    fig.update_yaxes(showgrid=False, ticklabelstandoff=6, tickfont={"color": t.ink_secondary})
    return fig


def monthly_trend(
    df: pd.DataFrame, t: Theme, currency: str, income: float, selected: str | None = None
) -> go.Figure:
    """Stacked columns per month by bucket with the monthly income as a reference line."""
    fig = go.Figure()
    buckets = [b for b in (*BUCKETS, UNMAPPED) if b in set(df["bucket"])]
    for bucket in buckets:
        part = df[df["bucket"] == bucket]
        fig.add_bar(
            x=part["month"],
            y=part["amount"],
            name=bucket,
            marker={
                "color": t.buckets[bucket],
                "line": {"color": t.surface, "width": 2},  # 2px surface gap between segments
                "opacity": [1.0 if selected in (None, m) else 0.45 for m in part["month"]],
            },
            hovertemplate=f"{bucket}<br>%{{x}}: %{{y:,.0f}} {currency}<extra></extra>",
        )
    _layout(fig, t, height=340, currency=currency, barmode="stack", hovermode="x unified")
    fig.update_layout(legend_traceorder="normal")
    fig.update_traces(selector={"type": "bar"}, marker_cornerradius=BAR_RADIUS)
    if income > 0:
        fig.add_hline(
            y=income,
            line={"color": t.muted, "width": 1},
            annotation={
                "text": f"Income {income:,.0f}".replace(",", " "),
                "font": {"color": t.muted, "size": 12},
                "xanchor": "left",
            },
            annotation_position="top left",
        )
    fig.update_xaxes(type="category", showgrid=False)
    fig.update_yaxes(tickformat=",.0f")
    return fig


def savings(df: pd.DataFrame, t: Theme, currency: str, selected: str | None = None) -> go.Figure:
    """Monthly saved (close - open) as columns; negative months in red with a label."""
    df = df.dropna(subset=["remaining"])
    colors = [t.critical if v < 0 else t.ink_secondary for v in df["remaining"]]
    opacity = [1.0 if selected in (None, m) else 0.45 for m in df["month"]]
    fig = go.Figure(
        go.Bar(
            x=df["month"],
            y=df["remaining"],
            marker={"color": colors, "opacity": opacity, "cornerradius": BAR_RADIUS},
            text=[f"▼ {v:,.0f}".replace(",", " ") if v < 0 else "" for v in df["remaining"]],
            textposition="outside",
            textfont={"color": t.ink_secondary},
            customdata=df[["open", "close"]].to_numpy(),
            hovertemplate=(
                f"%{{x}}<br>Saved %{{y:,.0f}} {currency}"
                f"<br>Open %{{customdata[0]:,.0f}} → Close %{{customdata[1]:,.0f}}<extra></extra>"
            ),
        )
    )
    _layout(fig, t, height=260, currency=currency, showlegend=False, bargap=0.5)
    fig.update_xaxes(type="category", showgrid=False)
    fig.update_yaxes(tickformat=",.0f")
    return fig


def top_bars(df: pd.DataFrame, label: str, t: Theme, currency: str, color: str) -> go.Figure:
    """Horizontal bars, single series, value at the tip."""
    df = df.iloc[::-1]
    fig = go.Figure(
        go.Bar(
            y=df[label].astype(str),
            x=df["amount"],
            orientation="h",
            marker={"color": color, "cornerradius": BAR_RADIUS},
            width=0.6,
            text=[f"{v:,.0f}".replace(",", " ") for v in df["amount"]],
            textposition="outside",
            textfont={"color": t.ink_secondary, "size": 12},
            cliponaxis=False,
            customdata=df["count"],
            hovertemplate=(
                f"%{{y}}<br>%{{x:,.0f}} {currency} · %{{customdata}} row(s)<extra></extra>"
            ),
        )
    )
    _layout(fig, t, height=max(140, 30 * len(df) + 40), currency=currency, showlegend=False)
    xmax = float(df["amount"].max() if len(df) else 1) * 1.2
    fig.update_xaxes(range=[0, xmax], showgrid=True)
    fig.update_yaxes(showgrid=False, tickfont={"color": t.ink_secondary})
    return fig
