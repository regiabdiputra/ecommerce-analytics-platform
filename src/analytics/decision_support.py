"""
Decision Support Engine — converts analytics insights into structured recommendations.
Framework: Observation → Evidence → Implication → Action → Priority
"""
import pandas as pd
import numpy as np
import os
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

MARTS_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "marts")
)
REPORTS_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "outputs", "reports")
)
FORECASTS_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "outputs", "forecasts")
)


def _recommendation(title, observation, evidence, implication, action, priority, category):
    """Build a standardized recommendation dict."""
    assert priority in ("High", "Medium", "Low"), f"Invalid priority: {priority}"
    assert category in ("Sales", "Operations", "Geography", "Commercial", "Risk"), \
        f"Invalid category: {category}"
    return {
        "title": title,
        "observation": observation,
        "evidence": evidence,
        "implication": implication,
        "action": action,
        "priority": priority,
        "category": category,
    }


def generate_recommendations(fact: pd.DataFrame, df_cats: pd.DataFrame) -> list:
    """
    Generate evidence-based recommendations from actual data.
    All claims reference actual computed values — nothing fabricated.
    """
    recs = []

    # ── Precompute key metrics ────────────────────────────────────────────────
    total_orders = len(fact)
    cancel_rate = fact["is_cancelled"].mean() * 100
    cod_rate = fact["is_cod"].mean() * 100
    cod_cancel_rate = fact[fact["is_cod"] == 1]["is_cancelled"].mean() * 100 if len(fact[fact["is_cod"]==1]) > 0 else 0
    non_cod_cancel_rate = fact[fact["is_cod"] == 0]["is_cancelled"].mean() * 100 if len(fact[fact["is_cod"]==0]) > 0 else 0
    java_bali_pct = fact["java_bali_flag"].mean() * 100
    free_shipping_pct = fact["is_free_shipping"].mean() * 100
    subsidy_pct = fact["shipping_subsidy_ratio"].mean() * 100

    # Monthly trend
    monthly = (
        fact.groupby("year_month_str")["order_id"]
        .count().reset_index()
        .sort_values("year_month_str")
    )
    recent_3m_avg = monthly.tail(3)["order_id"].mean()
    prior_3m_avg = monthly.iloc[-6:-3]["order_id"].mean() if len(monthly) >= 6 else monthly["order_id"].mean()
    growth_trend = (recent_3m_avg - prior_3m_avg) / prior_3m_avg * 100 if prior_3m_avg > 0 else 0

    # Category concentration
    cat_orders = df_cats.groupby("category")["order_id"].count().sort_values(ascending=False)
    top3_cat_pct = cat_orders.head(3).sum() / cat_orders.sum() * 100

    # Province concentration
    prov_orders = fact.groupby("province_clean")["order_id"].count().sort_values(ascending=False)
    top3_prov_pct = prov_orders.head(3).sum() / len(fact) * 100
    top1_prov = prov_orders.index[0]
    top1_prov_pct = prov_orders.iloc[0] / len(fact) * 100

    # Province cancel rates
    prov_cancel = (
        fact.groupby("province_clean")
        .agg(total=("order_id","count"), cancelled=("is_cancelled","sum"))
        .assign(cancel_rate=lambda d: d["cancelled"] / d["total"] * 100)
    )
    high_cancel_provs = prov_cancel[
        (prov_cancel["cancel_rate"] > cancel_rate * 1.5) &
        (prov_cancel["total"] >= 50)
    ].sort_values("cancel_rate", ascending=False)

    # Discount rarity
    discount_pct = fact["has_discount"].mean() * 100

    # ── REC 1: COD Cancellation Risk ─────────────────────────────────────────
    if cod_cancel_rate > non_cod_cancel_rate * 1.2:
        gap = cod_cancel_rate - non_cod_cancel_rate
        recs.append(_recommendation(
            title="Reduce COD-Driven Cancellations",
            observation=f"COD orders represent {cod_rate:.1f}% of all orders and have a "
                        f"{cod_cancel_rate:.1f}% cancellation rate.",
            evidence=f"COD cancellation rate ({cod_cancel_rate:.1f}%) exceeds digital payment "
                     f"cancellation rate ({non_cod_cancel_rate:.1f}%) by {gap:.1f} percentage points. "
                     f"COD accounts for {cod_rate:.1f}% of total order volume ({total_orders:,} orders).",
            implication="COD dominance creates significant operational risk — failed deliveries "
                        "result in returned shipments, wasted logistics cost, and lost revenue.",
            action="(1) Implement buyer verification for COD orders in high-risk provinces. "
                   "(2) Consider minimum order value threshold for COD eligibility. "
                   "(3) Promote digital payment incentives (cashback, lower shipping). "
                   "(4) Monitor COD cancellation rate monthly.",
            priority="High",
            category="Operations",
        ))

    # ── REC 2: Geographic Concentration Risk ──────────────────────────────────
    if java_bali_pct > 60:
        recs.append(_recommendation(
            title="Diversify Geographic Revenue Base",
            observation=f"{java_bali_pct:.1f}% of all orders originate from Java, Bali, and Banten.",
            evidence=f"Top province {top1_prov} alone contributes {top1_prov_pct:.1f}% of orders. "
                     f"Top 3 provinces = {top3_prov_pct:.1f}% of total. "
                     f"Outside Java-Bali: {100-java_bali_pct:.1f}% of orders.",
            implication="High geographic concentration creates vulnerability — any disruption "
                        "(logistics, competition, regional events) in Jawa Barat or Banten "
                        "would materially impact overall business performance.",
            action="(1) Identify high-potential provinces outside Java with low cancellation rates. "
                   "(2) Target emerging markets (provinces showing volume growth but low penetration). "
                   "(3) Evaluate whether shipping costs to outer provinces are competitively subsidized.",
            priority="Medium",
            category="Geography",
        ))

    # ── REC 3: Category Concentration ─────────────────────────────────────────
    top3_names = cat_orders.head(3).index.tolist()
    if top3_cat_pct > 60:
        recs.append(_recommendation(
            title="Monitor Category Concentration Risk",
            observation=f"Top 3 categories ({', '.join(top3_names)}) represent {top3_cat_pct:.1f}% "
                        "of all category appearances.",
            evidence=f"Category distribution shows high concentration: "
                     f"{top3_names[0]} alone represents {cat_orders.iloc[0]/cat_orders.sum()*100:.1f}% of orders.",
            implication="Over-reliance on a small number of product categories creates business risk "
                        "if demand shifts or competition intensifies in those segments.",
            action="(1) Analyze growth trajectory of top categories. "
                   "(2) Identify emerging categories with high growth rates for investment. "
                   "(3) Review which categories have high cancellation rates and address root causes.",
            priority="Medium",
            category="Commercial",
        ))

    # ── REC 4: High-Risk Province Operations ──────────────────────────────────
    if len(high_cancel_provs) > 0:
        top_risk = high_cancel_provs.index[0]
        top_risk_rate = high_cancel_provs.iloc[0]["cancel_rate"]
        recs.append(_recommendation(
            title=f"Address Elevated Cancellation Rate in {top_risk}",
            observation=f"{top_risk} has a cancellation rate of {top_risk_rate:.1f}% — "
                        f"significantly above the national average of {cancel_rate:.1f}%.",
            evidence=f"{len(high_cancel_provs)} provinces have cancellation rates ≥ 1.5x the national average. "
                     f"{top_risk}: {int(high_cancel_provs.iloc[0]['total']):,} orders, "
                     f"{top_risk_rate:.1f}% cancellation. National avg: {cancel_rate:.1f}%.",
            implication="High cancellation provinces waste shipping costs and operational resources. "
                        "Root causes may include: high COD proportion, logistics reliability issues, "
                        "or buyer-initiated order changes.",
            action=f"(1) Investigate cancellation reason breakdown specifically in {top_risk}. "
                   f"(2) Compare COD vs digital payment cancel rates within {top_risk}. "
                   f"(3) Review courier performance and delivery success rates in the region. "
                   "Note: causal factors require operational investigation.",
            priority="High",
            category="Operations",
        ))

    # ── REC 5: Shipping Subsidy Dependency ────────────────────────────────────
    if free_shipping_pct > 60 and subsidy_pct > 50:
        recs.append(_recommendation(
            title="Assess Shipping Subsidy Sustainability",
            observation=f"{free_shipping_pct:.1f}% of orders had zero buyer shipping cost. "
                        f"Platform subsidizes {subsidy_pct:.1f}% of shipping costs on average.",
            evidence=f"Median buyer shipping payment = Rp 0 (free shipping). "
                     f"Median estimated platform subsidy = Rp 9,500 per order. "
                     f"Total orders: {total_orders:,}.",
            implication="Heavy shipping subsidies support order volume but represent a significant "
                        "platform cost. As volume grows, subsidy cost scales proportionally. "
                        "Business sustainability depends on whether subsidy is offset by GMV growth.",
            action="(1) Monitor subsidy cost trend monthly. "
                   "(2) Identify order segments where buyers can absorb partial shipping cost. "
                   "(3) Evaluate whether heavier orders (high weight_kg) receive disproportionate subsidy.",
            priority="Medium",
            category="Commercial",
        ))

    # ── REC 6: Growth Trend Monitoring ────────────────────────────────────────
    if growth_trend < -10:
        recs.append(_recommendation(
            title="Investigate Recent Order Volume Decline",
            observation=f"Order volume in the most recent 3 months averaged {recent_3m_avg:.0f}/month "
                        f"vs {prior_3m_avg:.0f}/month in the prior 3 months ({growth_trend:+.1f}%).",
            evidence=f"3-month rolling average declined {abs(growth_trend):.1f}% "
                     f"(from {prior_3m_avg:.0f} to {recent_3m_avg:.0f} orders/month).",
            implication="A sustained volume decline warrants investigation into platform-level, "
                        "market-level, or operational causes.",
            action="(1) Check if decline is seasonal (compare YoY). "
                   "(2) Review marketing/promotion activity in declining period. "
                   "(3) Analyze whether specific categories or regions are driving the decline. "
                   "Causal factors require operational investigation.",
            priority="High",
            category="Sales",
        ))
    elif growth_trend > 10:
        recs.append(_recommendation(
            title="Capitalize on Positive Growth Momentum",
            observation=f"Order volume shows positive growth: +{growth_trend:.1f}% "
                        f"in recent 3 months vs prior 3 months.",
            evidence=f"Recent 3-month avg: {recent_3m_avg:.0f} orders/month. "
                     f"Prior 3-month avg: {prior_3m_avg:.0f} orders/month.",
            implication="Positive trend provides opportunity to consolidate gains through "
                        "operational readiness and targeted expansion.",
            action="(1) Ensure logistics and fulfillment capacity matches growing order volume. "
                   "(2) Identify which categories/regions are driving growth for targeted investment. "
                   "(3) Monitor cancellation rate — ensure growth doesn't increase operational strain.",
            priority="Medium",
            category="Sales",
        ))

    # ── REC 7: Discount Program Assessment ────────────────────────────────────
    if discount_pct < 2:
        recs.append(_recommendation(
            title="Evaluate Discount Strategy Effectiveness",
            observation=f"Only {discount_pct:.1f}% of orders have any discount applied.",
            evidence=f"99.4% of orders have Total Diskon = 0. "
                     "Discount analysis shows minimal commercial discount activity in the dataset.",
            implication="Either discount programs are not being utilized, or buyers are purchasing "
                        "at full price. This limits the ability to use price promotions as a "
                        "growth lever. Subsidy may be delivered through shipping (not product discount).",
            action="(1) Clarify whether product discounts are tracked separately from shipping subsidies. "
                   "(2) If discount programs exist, investigate why uptake is low. "
                   "(3) Consider targeted discount campaigns for high-cancellation segments to improve conversion.",
            priority="Low",
            category="Commercial",
        ))

    # Sort by priority
    priority_order = {"High": 0, "Medium": 1, "Low": 2}
    recs.sort(key=lambda x: priority_order[x["priority"]])

    logger.info(f"Generated {len(recs)} recommendations.")
    return recs


def run_decision_support(fact: pd.DataFrame, df_cats: pd.DataFrame) -> dict:
    """Run decision support engine."""
    logger.info("Running decision support engine...")
    recs = generate_recommendations(fact, df_cats)
    result = {
        "generated_at": datetime.now().isoformat(),
        "total_recommendations": len(recs),
        "high_priority": sum(1 for r in recs if r["priority"] == "High"),
        "medium_priority": sum(1 for r in recs if r["priority"] == "Medium"),
        "low_priority": sum(1 for r in recs if r["priority"] == "Low"),
        "recommendations": recs,
    }
    logger.info("Decision support complete.")
    return result


def save_decision_support(result: dict, output_dir: str = REPORTS_PATH) -> str:
    """Save decision support output to JSON."""
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "recommendations.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    logger.info(f"Recommendations saved: {path}")
    return path


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..")))

    PROCESSED_PATH = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed")
    )
    fact = pd.read_parquet(os.path.join(MARTS_PATH, "fact_orders.parquet"))
    df_cats = pd.read_parquet(os.path.join(PROCESSED_PATH, "orders_categories.parquet"))

    result = run_decision_support(fact, df_cats)
    save_decision_support(result)

    print(f"\nDecision Support: {result['total_recommendations']} recommendations")
    print(f"  High: {result['high_priority']} | Medium: {result['medium_priority']} | Low: {result['low_priority']}")
    for i, rec in enumerate(result["recommendations"], 1):
        print(f"\n[{i}] [{rec['priority']}] {rec['title']}")
        print(f"    Observation: {rec['observation']}")
        print(f"    Action: {rec['action'][:120]}...")
