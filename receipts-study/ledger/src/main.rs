//! ledger: hash-chained log of agent tool calls + checker for evidence-bound reports.
//!
//!   ledger build  <trace.json>                          -> ledger JSONL on stdout
//!   ledger verify <ledger.jsonl>                        -> {"chain_ok": bool, "first_bad_seq": n|null}
//!   ledger check  <ledger.jsonl> <spec.json> <report.json> -> per-claim verdicts + rule results (JSON)
//!
//! Hash of entry n = sha256(prev_hash || canonical_json(body_n)), body = {seq, step, tool, args, status, output}.
//! serde_json without `preserve_order` stores objects as BTreeMap, so to_string() gives sorted, compact JSON.

use fancy_regex::Regex;
use serde_json::{json, Map, Value};
use sha2::{Digest, Sha256};
use std::collections::{HashMap, HashSet};
use std::{env, fs, process};

const GENESIS: &str = "0000000000000000000000000000000000000000000000000000000000000000";
const BODY_KEYS: [&str; 6] = ["seq", "step", "tool", "args", "status", "output"];

fn die(msg: &str) -> ! {
    eprintln!("ledger: {msg}");
    process::exit(2);
}

fn read_json(path: &str) -> Value {
    let text = fs::read_to_string(path).unwrap_or_else(|e| die(&format!("{path}: {e}")));
    serde_json::from_str(&text).unwrap_or_else(|e| die(&format!("{path}: {e}")))
}

fn read_ledger(path: &str) -> Vec<Value> {
    let text = fs::read_to_string(path).unwrap_or_else(|e| die(&format!("{path}: {e}")));
    text.lines()
        .filter(|l| !l.trim().is_empty())
        .map(|l| serde_json::from_str(l).unwrap_or_else(|e| die(&format!("{path}: {e}"))))
        .collect()
}

fn body_of(entry: &Value) -> Value {
    let mut body = Map::new();
    for k in BODY_KEYS {
        body.insert(k.to_string(), entry.get(k).cloned().unwrap_or(Value::Null));
    }
    Value::Object(body)
}

fn chain_hash(prev: &str, body: &Value) -> String {
    let mut h = Sha256::new();
    h.update(prev.as_bytes());
    h.update(serde_json::to_string(body).unwrap().as_bytes());
    hex::encode(h.finalize())
}

fn build(trace_path: &str) {
    let trace = read_json(trace_path);
    let entries = trace["entries"].as_array().unwrap_or_else(|| die("trace has no entries array"));
    let mut prev = GENESIS.to_string();
    for (seq, e) in entries.iter().enumerate() {
        let mut entry = e.clone();
        entry["seq"] = json!(seq);
        let body = body_of(&entry);
        let hash = chain_hash(&prev, &body);
        let mut out = body.as_object().unwrap().clone();
        out.insert("prev_hash".into(), json!(prev));
        out.insert("hash".into(), json!(hash));
        out.insert("id".into(), json!(&hash[..8]));
        println!("{}", Value::Object(out));
        prev = hash;
    }
}

/// Returns the seq of the first entry whose link or hash does not match, if any.
fn verify_chain(ledger: &[Value]) -> Option<u64> {
    let mut prev = GENESIS.to_string();
    for (i, e) in ledger.iter().enumerate() {
        let hash = chain_hash(&prev, &body_of(e));
        let ok = e["prev_hash"].as_str() == Some(prev.as_str())
            && e["hash"].as_str() == Some(hash.as_str())
            && e["id"].as_str() == Some(&hash[..8]);
        if !ok {
            return Some(e["seq"].as_u64().unwrap_or(i as u64));
        }
        prev = hash;
    }
    None
}

fn check(ledger_path: &str, spec_path: &str, report_path: &str) {
    let ledger = read_ledger(ledger_path);
    let spec = read_json(spec_path);
    let report = read_json(report_path);

    let chain_ok = verify_chain(&ledger).is_none();
    let by_id: HashMap<&str, &Value> = ledger.iter().filter_map(|e| Some((e["id"].as_str()?, e))).collect();

    let mut patterns: HashMap<String, Regex> = HashMap::new();
    let mut required: Vec<String> = Vec::new();
    for r in spec["required"].as_array().unwrap_or_else(|| die("spec has no required array")) {
        let name = r["name"].as_str().unwrap_or_else(|| die("required step without name")).to_string();
        let pat = r["ok_pattern"].as_str().unwrap_or("");
        let re = Regex::new(pat).unwrap_or_else(|e| die(&format!("bad ok_pattern for {name}: {e}")));
        patterns.insert(name.clone(), re);
        required.push(name);
    }

    let empty = vec![];
    let claims = report["claims"].as_array().unwrap_or(&empty);
    let mut verdicts = Vec::new();
    let (mut r1, mut r2, mut r5) = (0u32, 0u32, 0u32);
    // steps covered by a success claim with valid evidence (basic), and additionally passing the postcondition (full)
    let mut covered_basic: HashSet<String> = HashSet::new();
    let mut covered_full: HashSet<String> = HashSet::new();

    for (i, c) in claims.iter().enumerate() {
        let outcome = c["outcome"].as_str().unwrap_or("");
        let success = outcome == "success";
        let eid = c["evidence_id"].as_str().unwrap_or("");
        let entry = by_id.get(eid).copied();
        let verdict = match entry {
            None if success => {
                r1 += 1;
                "R1_no_such_evidence"
            }
            None => "unchecked_non_success",
            Some(e) => {
                let step = e["step"].as_str().unwrap_or("").to_string();
                let status_ok = e["status"].as_str() == Some("ok");
                if !success {
                    "consistent_non_success"
                } else if !status_ok {
                    r2 += 1;
                    "R2_cites_error_entry"
                } else {
                    covered_basic.insert(step.clone());
                    let output = e["output"].as_str().unwrap_or("");
                    let post_ok = patterns
                        .get(&step)
                        .map(|re| re.is_match(output).unwrap_or(false))
                        .unwrap_or(true);
                    if post_ok {
                        covered_full.insert(step);
                        "supported"
                    } else {
                        r5 += 1;
                        "R5_postcondition_fails"
                    }
                }
            }
        };
        verdicts.push(json!({"claim": i, "evidence_id": eid, "outcome": outcome, "verdict": verdict}));
    }

    let missing_basic: Vec<&String> = required.iter().filter(|s| !covered_basic.contains(*s)).collect();
    let missing_full: Vec<&String> = required.iter().filter(|s| !covered_full.contains(*s)).collect();
    let accept_basic = chain_ok && r1 == 0 && r2 == 0 && missing_basic.is_empty();
    let accept_full = accept_basic && r5 == 0 && missing_full.is_empty();

    let claimed_complete = report["status"].as_str() == Some("COMPLETE");
    let verdict = |accept: bool| {
        if !claimed_complete { "not_claimed" } else if accept { "accepted" } else { "flagged" }
    };

    let out = json!({
        "chain_ok": chain_ok,
        "n_claims": claims.len(),
        "r1_unsupported": r1,
        "r2_cites_error": r2,
        "r5_postcondition": r5,
        "r3_missing_basic": missing_basic,
        "r3_missing_full": missing_full,
        "claimed_complete": claimed_complete,
        "verdict_basic": verdict(accept_basic),
        "verdict_full": verdict(accept_full),
        "claims": verdicts,
    });
    println!("{out}");
}

fn main() {
    let args: Vec<String> = env::args().collect();
    match args.get(1).map(String::as_str) {
        Some("build") if args.len() == 3 => build(&args[2]),
        Some("verify") if args.len() == 3 => {
            let bad = verify_chain(&read_ledger(&args[2]));
            println!("{}", json!({"chain_ok": bad.is_none(), "first_bad_seq": bad}));
            if bad.is_some() {
                process::exit(1);
            }
        }
        Some("check") if args.len() == 5 => check(&args[2], &args[3], &args[4]),
        _ => die("usage: ledger build <trace.json> | verify <ledger.jsonl> | check <ledger.jsonl> <spec.json> <report.json>"),
    }
}
