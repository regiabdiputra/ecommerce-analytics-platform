"""
run_pipeline.py — Master pipeline orchestrator.
Runs all steps sequentially from raw data to analytics outputs.
Usage: python run_pipeline.py
"""
import sys
import os
import logging
import time

# Force UTF-8 output on Windows to avoid cp1252 encoding errors
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("outputs/reports/pipeline_run.log", mode="w", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)


def step(name: str):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            logger.info(f"\n{'='*60}")
            logger.info(f"  STEP: {name}")
            logger.info(f"{'='*60}")
            t0 = time.time()
            result = fn(*args, **kwargs)
            elapsed = time.time() - t0
            logger.info(f"  [DONE] {name} completed in {elapsed:.1f}s")
            return result
        return wrapper
    return decorator


@step("1. Ingestion — Load Raw Data")
def run_ingestion():
    from src.ingestion.ingest import load_raw, get_raw_stats
    df = load_raw()
    stats = get_raw_stats(df)
    logger.info(f"  Rows: {stats['rows']:,} | Columns: {stats['columns']}")
    return df


@step("2. Validation — Data Quality Checks")
def run_validation(df):
    from src.validation.validate import validate, print_report, save_report
    import os
    os.makedirs("outputs/reports", exist_ok=True)
    report = validate(df)
    print_report(report)
    save_report(report)
    if report["summary"]["failed"] > 0:
        logger.error("CRITICAL: Validation failed. Pipeline halted.")
        sys.exit(1)
    return report


@step("3. Staging — Normalize and Clean")
def run_staging(df):
    from src.transformation.staging import run_staging, save_staging
    stg = run_staging(df)
    save_staging(stg)
    return stg


@step("4. Transformation — Feature Engineering")
def run_transformation(stg):
    from src.transformation.transform import build_features, build_category_exploded, save_processed
    enriched = build_features(stg)
    cats = build_category_exploded(enriched)
    save_processed(enriched, cats)
    return enriched, cats


@step("5. Dimensional Model — Star Schema")
def run_modeling(enriched, cats):
    from src.modeling.build_model import build_dimensional_model, save_model
    model = build_dimensional_model(enriched, cats)
    save_model(model)
    return model


@step("6. KPI Layer — Business Metrics")
def run_kpis(fact, cats):
    from src.analytics.kpi import compute_kpis, compute_monthly_kpis, compute_category_kpis, compute_geo_kpis, save_kpi_report
    kpis = compute_kpis(fact)
    monthly = compute_monthly_kpis(fact)
    save_kpi_report(kpis, monthly)
    return kpis, monthly


@step("7. Sales Analytics")
def run_sales(fact, cats):
    from src.analytics.sales_analytics import run_sales_analytics, save_sales_analytics
    results = run_sales_analytics(fact, cats)
    save_sales_analytics(results)
    return results


@step("8. Operations Analytics")
def run_operations(fact):
    from src.analytics.operations_analytics import run_operations_analytics, save_operations_analytics
    results = run_operations_analytics(fact)
    save_operations_analytics(results)
    return results


@step("9. Geographic Analytics")
def run_geo(fact):
    from src.analytics.geo_analytics import run_geo_analytics, save_geo_analytics
    results = run_geo_analytics(fact)
    save_geo_analytics(results)
    return results


@step("10. Segmentation Analysis")
def run_segmentation(fact, cats):
    from src.analytics.segmentation import run_segmentation, save_segmentation
    results = run_segmentation(fact, cats)
    save_segmentation(results)
    return results


@step("11. Forecasting")
def run_forecasting(fact):
    from src.forecasting.forecaster import run_forecasting, save_forecast
    result = run_forecasting(fact, horizon=3)
    save_forecast(result)
    return result


@step("12. Anomaly Detection")
def run_anomaly(fact):
    from src.monitoring.anomaly_detection import detect_all_anomalies, save_anomaly_report
    result = detect_all_anomalies(fact)
    save_anomaly_report(result)
    return result


@step("13. Early Warning System")
def run_early_warning(fact):
    from src.monitoring.early_warning import run_early_warning, save_early_warning
    result = run_early_warning(fact)
    save_early_warning(result)
    return result


@step("14. Decision Support")
def run_decision_support(fact, cats):
    from src.analytics.decision_support import run_decision_support, save_decision_support
    result = run_decision_support(fact, cats)
    save_decision_support(result)
    return result


def main():
    total_start = time.time()
    logger.info("\n" + "="*60)
    logger.info("  INTELLIGENT SALES & OPERATIONS ANALYTICS PLATFORM")
    logger.info("  Pipeline Execution Start")
    logger.info("="*60)

    os.makedirs("outputs/reports", exist_ok=True)
    os.makedirs("outputs/forecasts", exist_ok=True)
    os.makedirs("outputs/figures", exist_ok=True)

    # Run pipeline
    df       = run_ingestion()
    _        = run_validation(df)
    stg      = run_staging(df)
    enriched, cats = run_transformation(stg)
    model    = run_modeling(enriched, cats)

    fact = model["fact_orders"]

    kpis, monthly    = run_kpis(fact, cats)
    sales_results    = run_sales(fact, cats)
    ops_results      = run_operations(fact)
    geo_results      = run_geo(fact)
    seg_results      = run_segmentation(fact, cats)
    forecast_result  = run_forecasting(fact)
    anomaly_result   = run_anomaly(fact)
    warning_result   = run_early_warning(fact)
    decision_result  = run_decision_support(fact, cats)

    total_elapsed = time.time() - total_start

    logger.info("\n" + "="*60)
    logger.info("  PIPELINE COMPLETE")
    logger.info(f"  Total time: {total_elapsed:.1f}s")
    logger.info("="*60)
    logger.info(f"\n  Total Orders    : {kpis['total_orders']['value']:,}")
    logger.info(f"  Cancel Rate     : {kpis['cancellation_rate']['value']:.1f}%")
    logger.info(f"  Total Revenue   : Rp {kpis['total_revenue']['value']:,}")
    logger.info(f"  Avg Order Value : Rp {kpis['avg_order_value']['value']:,.0f}")

    fc = forecast_result.get("forecast")
    if fc is not None and hasattr(fc, "to_dict"):
        logger.info(f"\n  3-Month Forecast:")
        for _, row in fc.iterrows():
            logger.info(f"    {row['year_month_str']}: {row['forecast_orders']:,} orders "
                        f"(CI: {row['ci_lower']:,}–{row['ci_upper']:,})")

    ew = warning_result["summary"]
    logger.info(f"\n  Early Warnings  : {ew['total_alerts']} alerts "
                f"({ew['critical']} Critical, {ew['warning']} Warning, {ew['watch']} Watch)")

    ds = decision_result
    logger.info(f"  Recommendations : {ds['total_recommendations']} "
                f"({ds['high_priority']} High, {ds['medium_priority']} Medium, {ds['low_priority']} Low)")

    logger.info("\n  Run 'streamlit run dashboard/app.py' to view the dashboard.")


if __name__ == "__main__":
    main()
