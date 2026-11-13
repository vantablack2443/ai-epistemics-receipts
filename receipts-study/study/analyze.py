"""Metrics, bootstrap CIs and figures from data/graded/graded.jsonl -> out/.

Bootstrap resamples base tasks (all rows of a task move together), 10,000 resamples.
PROSE vs RECEIPTS is compared per model with an exact McNemar test on paired (task, condition) items.
"""
import json
from collections import defaultdict
from math import comb
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out"
FAIL_CONDS = ["loud", "quiet", "absent"]
FORMATS = ["PROSE", "RECEIPTS"]
N_BOOT = 10_000


def boot_rate(rows, pred, keep, seed=0):
    """Rate of pred among rows passing keep, with a 95% CI from resampling task_ids."""
    rows = [r for r in rows if keep(r)]
    if not rows:
        return None
    by_task = defaultdict(list)
    for r in rows:
        by_task[r["task_id"]].append(1.0 if pred(r) else 0.0)
    tasks = list(by_task)
    sums = np.array([sum(by_task[t]) for t in tasks])
    counts = np.array([len(by_task[t]) for t in tasks])
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(tasks), size=(N_BOOT, len(tasks)))
    boots = sums[idx].sum(1) / counts[idx].sum(1)
    return {"rate": float(sums.sum() / counts.sum()), "lo": float(np.percentile(boots, 2.5)),
            "hi": float(np.percentile(boots, 97.5)), "n": int(counts.sum())}


def mcnemar_exact(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


def fmt_ci(x):
    return "n/a" if x is None else f"{x['rate']:.2f} [{x['lo']:.2f}, {x['hi']:.2f}] (n={x['n']})"


def main():
    rows = [json.loads(l) for l in (ROOT / "data" / "graded" / "graded.jsonl").read_text().splitlines() if l.strip()]
    OUT.mkdir(exist_ok=True)
    models = sorted({r["model"] for r in rows})
    m = {"models": models, "fsr": {}, "fsr_all_fail": {}, "false_alarm": {}, "parse": {}, "mcnemar": {},
         "verifier": {}, "receipts": {}}
    md = ["# Results\n", "Rates with 95% bootstrap CIs over base tasks. Rows with no parsable STATUS are excluded "
          "from FSR / false-alarm and reported under parse rates.\n"]

    for model in models:
        mr = [r for r in rows if r["model"] == model]
        for fmt in FORMATS:
            fr = [r for r in mr if r["format"] == fmt]
            k = f"{model}|{fmt}"
            m["fsr"][k] = {c: boot_rate(fr, lambda r: r["false_success"],
                                        lambda r, c=c: r["condition"] == c and r["status_ok"]) for c in FAIL_CONDS}
            m["fsr_all_fail"][k] = boot_rate(fr, lambda r: r["false_success"],
                                             lambda r: r["condition"] != "control" and r["status_ok"])
            m["false_alarm"][k] = boot_rate(fr, lambda r: r["false_alarm"],
                                            lambda r: r["condition"] == "control" and r["status_ok"])
            m["parse"][k] = {"status_fail": sum(not r["status_ok"] for r in fr) / max(1, len(fr)),
                             "json_fail": (sum(not r.get("json_ok", True) for r in fr) / max(1, len(fr)))
                             if fmt == "RECEIPTS" else None, "n": len(fr)}

        # paired PROSE vs RECEIPTS on failure traces
        pairs = defaultdict(dict)
        for r in mr:
            if r["condition"] != "control" and r["status_ok"]:
                pairs[r["trace_id"]][r["format"]] = r["false_success"]
        both = [p for p in pairs.values() if len(p) == 2]
        b = sum(p["PROSE"] and not p["RECEIPTS"] for p in both)
        c = sum(p["RECEIPTS"] and not p["PROSE"] for p in both)
        m["mcnemar"][model] = {"pairs": len(both), "prose_only": b, "receipts_only": c, "p": mcnemar_exact(b, c)}

        # verifier coverage on RECEIPTS false-success reports
        fs = [r for r in mr if r["format"] == "RECEIPTS" and r["false_success"] and "verdict_basic" in r]
        basic = sum(r["verdict_basic"] == "flagged" for r in fs)
        full_only = sum(r["verdict_basic"] != "flagged" and r["verdict_full"] == "flagged" for r in fs)
        m["verifier"][model] = {"false_success_reports": len(fs), "caught_R1_R4": basic, "caught_only_R5": full_only,
                                "uncaught": len(fs) - basic - full_only,
                                "by_condition": {c: {"n": sum(r["condition"] == c for r in fs),
                                                     "caught_R1_R4": sum(r["condition"] == c and r["verdict_basic"] == "flagged" for r in fs),
                                                     "caught_with_R5": sum(r["condition"] == c and r["verdict_full"] == "flagged" for r in fs)}
                                                 for c in FAIL_CONDS}}
        # receipt validity over all claims; verifier false alarms on honest control reports
        rc = [r for r in mr if r["format"] == "RECEIPTS" and "n_claims" in r]
        n_claims = sum(r["n_claims"] for r in rc)
        ctrl_ok = [r for r in rc if r["condition"] == "control" and r["status"] == "COMPLETE"]
        m["receipts"][model] = {"claims": n_claims,
                                "unsupported_id_rate": sum(r["r1_unsupported"] for r in rc) / max(1, n_claims),
                                "cites_error_rate": sum(r["r2_cites_error"] for r in rc) / max(1, n_claims),
                                "control_complete_reports": len(ctrl_ok),
                                "verifier_false_flag_basic": sum(r["verdict_basic"] == "flagged" for r in ctrl_ok),
                                "verifier_false_flag_full": sum(r["verdict_full"] == "flagged" for r in ctrl_ok)}

    md.append("## False-success rate (STATUS: COMPLETE on an incomplete trace)\n")
    md.append("| model | format | loud | quiet | absent | all failures | false alarm (control) |")
    md.append("|---|---|---|---|---|---|---|")
    for k in m["fsr"]:
        model, fmt = k.split("|")
        cells = [fmt_ci(m["fsr"][k][c]) for c in FAIL_CONDS]
        md.append(f"| {model} | {fmt} | " + " | ".join(cells) + f" | {fmt_ci(m['fsr_all_fail'][k])} | {fmt_ci(m['false_alarm'][k])} |")
    md.append("\n## PROSE vs RECEIPTS (exact McNemar on paired failure traces)\n")
    md.append("| model | pairs | false success only in PROSE | only in RECEIPTS | p |")
    md.append("|---|---|---|---|---|")
    for model, v in m["mcnemar"].items():
        md.append(f"| {model} | {v['pairs']} | {v['prose_only']} | {v['receipts_only']} | {v['p']:.3g} |")
    md.append("\n## Verifier coverage of RECEIPTS false-success reports\n")
    md.append("| model | false-success reports | caught by R1-R4 | caught only with R5 | uncaught |")
    md.append("|---|---|---|---|---|")
    for model, v in m["verifier"].items():
        md.append(f"| {model} | {v['false_success_reports']} | {v['caught_R1_R4']} | {v['caught_only_R5']} | {v['uncaught']} |")
    md.append("\n## Receipt validity and parse rates\n")
    md.append("| model | claims | unsupported-id rate | cites-error rate | verifier false flags on honest control (basic / full) | STATUS parse fail PROSE / RECEIPTS | JSON parse fail |")
    md.append("|---|---|---|---|---|---|---|")
    for model in models:
        v = m["receipts"][model]
        pp, pr = m["parse"][f"{model}|PROSE"], m["parse"][f"{model}|RECEIPTS"]
        md.append(f"| {model} | {v['claims']} | {v['unsupported_id_rate']:.3f} | {v['cites_error_rate']:.3f} | "
                  f"{v['verifier_false_flag_basic']} / {v['verifier_false_flag_full']} of {v['control_complete_reports']} | "
                  f"{pp['status_fail']:.2f} / {pr['status_fail']:.2f} | {pr['json_fail']:.2f} |")

    (OUT / "metrics.json").write_text(json.dumps(m, indent=1))
    (OUT / "results.md").write_text("\n".join(md) + "\n")
    plot_fsr(m, models)
    plot_verifier(m, models)
    print(f"wrote {OUT / 'results.md'}, metrics.json, fig1_fsr.png, fig2_verifier.png")


def plot_fsr(m, models):
    fig, axes = plt.subplots(1, len(models), figsize=(4.2 * len(models), 3.4), sharey=True, squeeze=False)
    x = np.arange(len(FAIL_CONDS))
    colors = {"PROSE": "#8a8f98", "RECEIPTS": "#2a6fdb"}
    for ax, model in zip(axes[0], models):
        for j, fmt in enumerate(FORMATS):
            vals = [m["fsr"][f"{model}|{fmt}"][c] for c in FAIL_CONDS]
            rate = [v["rate"] if v else np.nan for v in vals]
            err = [[v["rate"] - v["lo"] if v else 0 for v in vals], [v["hi"] - v["rate"] if v else 0 for v in vals]]
            ax.bar(x + (j - 0.5) * 0.38, rate, 0.38, yerr=err, capsize=3, label=fmt, color=colors[fmt])
        ax.set_xticks(x, FAIL_CONDS)
        ax.set_title(model, fontsize=9)
        ax.set_ylim(0, 1)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0][0].set_ylabel("false-success rate")
    axes[0][0].legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "fig1_fsr.png", dpi=200)
    plt.close(fig)


def plot_verifier(m, models):
    fig, ax = plt.subplots(figsize=(1.6 + 1.4 * len(models), 3.2))
    parts = [("caught_R1_R4", "caught by R1-R4", "#2a6fdb"), ("caught_only_R5", "caught only with R5", "#8fb3f0"),
             ("uncaught", "uncaught", "#d9dce1")]
    bottom = np.zeros(len(models))
    for key, label, color in parts:
        vals = np.array([m["verifier"][mo][key] for mo in models], dtype=float)
        ax.bar(range(len(models)), vals, bottom=bottom, label=label, color=color)
        bottom += vals
    ax.set_xticks(range(len(models)), models, rotation=20, ha="right", fontsize=8)
    ax.set_ylabel("RECEIPTS false-success reports")
    ax.legend(frameon=False, fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "fig2_verifier.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    main()
