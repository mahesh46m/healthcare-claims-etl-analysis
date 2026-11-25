"""Aggregates, anomaly flags and charts on cleaned claims."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def provider_anomalies(good: pd.DataFrame, z_thresh=3.0):
    """Flag providers whose average billed amount (relative to the procedure norm) is a z-score outlier."""
    norm = good.groupby("procedure_code").billed_amount.transform("median")
    g = good.assign(billed_ratio=good.billed_amount / norm)
    prov = g.groupby("provider_id").agg(claims=("claim_id", "count"), avg_billed_ratio=("billed_ratio", "mean"))
    prov = prov[prov.claims >= 30]
    prov["z_score"] = (prov.avg_billed_ratio - prov.avg_billed_ratio.mean()) / prov.avg_billed_ratio.std()
    prov["flag"] = prov.z_score.abs() > z_thresh
    return prov.sort_values("z_score", ascending=False)


def run(good: pd.DataFrame, outdir="output"):
    paid = good[good.status == "PAID"]
    by_payer = good.groupby("payer").agg(
        claims=("claim_id", "count"),
        denial_rate=("status", lambda s: (s == "DENIED").mean()),
        billed=("billed_amount", "sum"), paid=("paid_amount", "sum"),
        avg_days_to_pay=("days_to_pay", "mean")).round(3)
    by_proc = good.groupby("procedure_code").agg(
        claims=("claim_id", "count"), avg_billed=("billed_amount", "mean"),
        avg_paid=("paid_amount", "mean")).round(2)
    monthly = good.assign(month=good.service_date.dt.to_period("M").astype(str)).groupby("month").agg(
        claims=("claim_id", "count"), billed=("billed_amount", "sum")).round(0)
    prov = provider_anomalies(good)

    by_payer.to_csv(f"{outdir}/summary_by_payer.csv")
    by_proc.to_csv(f"{outdir}/summary_by_procedure.csv")
    monthly.to_csv(f"{outdir}/summary_by_month.csv")
    prov[prov.flag].to_csv(f"{outdir}/flagged_providers.csv")

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(monthly.index, monthly.claims, color="#2b6cb0")
    ax.set_title("Synthetic claims per month (service date)")
    ax.set_ylabel("Claims"); plt.xticks(rotation=45); fig.tight_layout()
    fig.savefig(f"{outdir}/claims_per_month.png", dpi=120); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4))
    colors = prov.flag.map({True: "#c53030", False: "#a0aec0"})
    ax.scatter(prov.claims, prov.avg_billed_ratio, c=colors)
    for pid, r in prov[prov.flag].iterrows():
        ax.annotate(pid, (r.claims, r.avg_billed_ratio), xytext=(5, 5), textcoords="offset points")
    ax.set_title("Provider billing vs procedure median (red = flagged, |z| > 3)")
    ax.set_xlabel("Claims"); ax.set_ylabel("Avg billed / procedure median"); fig.tight_layout()
    fig.savefig(f"{outdir}/provider_anomalies.png", dpi=120); plt.close(fig)
    return by_payer, by_proc, prov
