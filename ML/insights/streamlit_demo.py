from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import streamlit as st


CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ML.insights.insight_orchestrator import orchestrate_insight
from ML.insights.models import ApplianceEvent


SCENARIOS = {
    "AC empty room": {
        "appliance": "ac",
        "power_watts": 900,
        "duration_minutes": 25,
        "occupied": False,
        "timestamp": "2026-05-20 14:20",
        "source": "direct_ct",
        "confidence": 0.99,
    },
    "Normal kettle": {
        "appliance": "kettle",
        "power_watts": 1800,
        "duration_minutes": 4,
        "occupied": True,
        "timestamp": "2026-05-20 07:10",
        "source": "nilm",
        "confidence": 0.96,
    },
    "Kettle unusual time": {
        "appliance": "kettle",
        "power_watts": 1800,
        "duration_minutes": 4,
        "occupied": True,
        "timestamp": "2026-05-20 03:10",
        "source": "nilm",
        "confidence": 0.96,
    },
    "Fridge health watch": {
        "appliance": "fridge",
        "power_watts": 190,
        "duration_minutes": 45,
        "occupied": False,
        "timestamp": "2026-05-20 13:00",
        "source": "nilm",
        "confidence": 0.86,
    },
    "High standby": {
        "appliance": "standby",
        "power_watts": 155,
        "duration_minutes": 300,
        "occupied": False,
        "timestamp": "2026-05-20 23:55",
        "source": "baseline",
        "confidence": 0.9,
    },
    "Unknown rice cooker": {
        "appliance": "rice_cooker",
        "power_watts": 620,
        "duration_minutes": 38,
        "occupied": True,
        "timestamp": "2026-05-20 18:40",
        "source": "profile_match",
        "confidence": 0.72,
    },
}


def parse_timestamp(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M")


def priority_color(priority: str) -> str:
    return {
        "critical": "#991b1b",
        "high": "#b91c1c",
        "medium": "#b45309",
        "low": "#166534",
    }.get(priority, "#334155")


def render_metric(label: str, value: str) -> None:
    st.markdown(
        f"""
        <div class="metric-box">
          <div class="metric-label">{label}</div>
          <div class="metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_insight_card(insight: dict[str, object]) -> None:
    priority = str(insight["priority"])
    color = priority_color(priority)
    reasons = insight.get("reasons", [])
    reason_html = "".join(f"<li>{reason}</li>" for reason in reasons)

    st.markdown(
        f"""
        <div class="insight-card" style="border-left-color: {color};">
          <div class="eyebrow">{priority.upper()} PRIORITY</div>
          <h3>{insight["title"]}</h3>
          <div class="device-row">
            <span>{str(insight["device"]).replace("_", " ").title()}</span>
            <span>{insight["source"]} · {insight["appliance_confidence_label"]}</span>
          </div>
          <ul>{reason_html}</ul>
          <div class="action">{insight["recommended_action"]}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def live_costs(power_watts: float, tariff_rm_per_kwh: float) -> dict[str, float]:
    cost_per_hour = (power_watts / 1000.0) * tariff_rm_per_kwh
    return {
        "per_hour": round(cost_per_hour, 2),
        "per_day": round(cost_per_hour * 24, 2),
        "per_month": round(cost_per_hour * 24 * 30, 2),
    }


def main() -> None:
    st.set_page_config(page_title="WattsEye Insight Prototype", layout="wide")
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.5rem; max-width: 1180px; }
        h1, h2, h3, p, div { letter-spacing: 0; }
        .metric-box {
            border: 1px solid #d6d3d1;
            border-radius: 8px;
            padding: 14px 16px;
            background: #ffffff;
            min-height: 92px;
        }
        .metric-label {
            color: #57534e;
            font-size: 13px;
            margin-bottom: 8px;
        }
        .metric-value {
            color: #1c1917;
            font-size: 24px;
            font-weight: 700;
            line-height: 1.15;
        }
        .insight-card {
            border: 1px solid #d6d3d1;
            border-left: 6px solid #166534;
            border-radius: 8px;
            padding: 18px;
            background: #fff;
        }
        .insight-card h3 {
            margin: 4px 0 10px;
            color: #1c1917;
            font-size: 24px;
        }
        .eyebrow {
            color: #57534e;
            font-size: 12px;
            font-weight: 700;
        }
        .device-row {
            display: flex;
            justify-content: space-between;
            gap: 12px;
            color: #57534e;
            font-size: 14px;
            border-top: 1px solid #e7e5e4;
            border-bottom: 1px solid #e7e5e4;
            padding: 10px 0;
            margin: 8px 0 12px;
            flex-wrap: wrap;
        }
        .insight-card ul {
            margin: 0 0 14px 18px;
            padding: 0;
            color: #292524;
        }
        .insight-card li {
            margin-bottom: 6px;
        }
        .action {
            background: #f5f5f4;
            border-radius: 8px;
            padding: 12px;
            color: #1c1917;
            font-weight: 600;
        }
        .small-muted {
            color: #78716c;
            font-size: 13px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("WattsEye Insight Prototype")
    st.caption("Minimal dashboard for testing routine, cost, occupancy, and health engines.")

    with st.sidebar:
        st.header("Test Input")
        selected = st.selectbox("Scenario", list(SCENARIOS.keys()))
        scenario = SCENARIOS[selected]

        appliance = st.selectbox(
            "Appliance",
            ["ac", "kettle", "fridge", "washing_machine", "hair_dryer", "iron", "standby", "rice_cooker"],
            index=["ac", "kettle", "fridge", "washing_machine", "hair_dryer", "iron", "standby", "rice_cooker"].index(
                scenario["appliance"]
            ),
        )
        power_watts = st.number_input("Power watts", min_value=0, max_value=5000, value=int(scenario["power_watts"]))
        duration_minutes = st.number_input(
            "Duration minutes",
            min_value=0,
            max_value=720,
            value=int(scenario["duration_minutes"]),
        )
        occupied = st.toggle("Room occupied", value=bool(scenario["occupied"]))
        timestamp_text = st.text_input("Timestamp", value=str(scenario["timestamp"]))
        source = st.selectbox(
            "Source",
            ["direct_ct", "nilm", "profile_match", "user_label", "baseline"],
            index=["direct_ct", "nilm", "profile_match", "user_label", "baseline"].index(str(scenario["source"])),
        )
        confidence = st.slider("Internal identification confidence", 0.0, 1.0, float(scenario["confidence"]), 0.01)
        tariff = st.number_input("Tariff RM/kWh", min_value=0.0, max_value=2.0, value=0.50, step=0.01)

    event = ApplianceEvent(
        timestamp=parse_timestamp(timestamp_text),
        appliance=appliance,
        power_watts=float(power_watts),
        duration_minutes=float(duration_minutes),
        occupied=occupied,
        source=source,
        confidence=confidence,
    )
    insight = orchestrate_insight(event, tariff_rm_per_kwh=tariff)
    current_cost = live_costs(float(power_watts), float(tariff))

    metric_cols = st.columns(5)
    with metric_cols[0]:
        render_metric("Current Device", str(insight["device"]).replace("_", " ").title())
    with metric_cols[1]:
        render_metric("Power", f"{insight['power_watts']:.0f} W")
    with metric_cols[2]:
        render_metric("Live Cost", f"RM{current_cost['per_hour']:.2f}/h")
    with metric_cols[3]:
        render_metric("If Left On", f"RM{current_cost['per_day']:.2f}/day")
    with metric_cols[4]:
        render_metric("Monthly Repeat", f"RM{insight['monthly_projection_rm']:.2f}")

    left, right = st.columns([1.15, 0.85], gap="large")
    with left:
        st.subheader("Live Cost")
        st.progress(min(float(power_watts) / 3000.0, 1.0))
        st.caption(
            f"At {power_watts:.0f}W and RM{tariff:.2f}/kWh: "
            f"RM{current_cost['per_hour']:.2f}/hour, "
            f"RM{current_cost['per_day']:.2f}/day, "
            f"RM{current_cost['per_month']:.2f}/month if continuously left on."
        )

        st.subheader("Priority Insight")
        render_insight_card(insight)

        st.subheader("Engine Breakdown")
        for result in insight["engine_results"]:
            with st.expander(f"{result['engine']} · {result['status']} · {result['priority']}"):
                st.json(result)

    with right:
        st.subheader("Mobile Card Preview")
        render_insight_card(insight)
        st.markdown('<div class="small-muted">This is the shape the Flutter app can consume later.</div>', unsafe_allow_html=True)

        st.subheader("Raw Dashboard JSON")
        st.json(insight)


if __name__ == "__main__":
    main()
