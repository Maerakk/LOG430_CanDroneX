"""Mesure du débit (k6) et du P95 d'activation (SQL). Partir d'une pile fraîche (docker compose down -v).

    python load-tests/run_measurement.py [--quick]
"""
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV = dict(line.split("=", 1) for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines()
           if "=" in line and not line.startswith("#"))
DATABASES = {"drone-db": "drone_management", "ordering-db": "service_ordering", "activation-db": "slice_activation"}


def sql(service: str, query: str) -> list[list[str]]:
    out = subprocess.run(["docker", "compose", "exec", "-T", "-e", f"MYSQL_PWD={ENV['MYSQL_ROOT_PASSWORD']}", service,
                          "mysql", "-uroot", "-N", "-B", DATABASES[service]],
                         input=query, cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [line.split("\t") for line in out.strip().splitlines()]


def seed_drones() -> None:
    if sql("drone-db", "SELECT COUNT(*) FROM drone WHERE drone_id LIKE 'LOAD-%';")[0][0] == "0":
        print("Chargement des 300 000 drones de mesure...")
        sql("drone-db", (ROOT / "load-tests/sql/seed_load_drones.sql").read_text(encoding="utf-8"))


def now_db() -> str:
    return sql("activation-db", "SELECT UTC_TIMESTAMP(6);")[0][0]


def sample_queue(samples: list, stop: threading.Event) -> None:
    while not stop.wait(5):
        rows = sql("activation-db", "SELECT UTC_TIMESTAMP(), SUM(state='PENDING'), SUM(state='ACTIVATING'), "
                                    "SUM(state='ACTIVE'), SUM(state='FAILED') FROM service;")
        ts, pending, activating, active, failed = rows[0]
        samples.append({"ts": ts, "pending": int(pending or 0), "activating": int(activating or 0),
                        "active": int(active or 0), "failed": int(failed or 0)})
        print(f"  [{ts}] en attente {pending} | en activation {activating} | actifs {active} | echecs {failed}")


def environment() -> dict:
    info = json.loads(subprocess.run(["docker", "info", "--format", "{{json .}}"], capture_output=True, text=True).stdout)
    return {"dockerCpus": info.get("NCPU"), "dockerMemoryGiB": round(info.get("MemTotal", 0) / 2**30, 1),
            "dockerOS": info.get("OperatingSystem"), "kernel": info.get("KernelVersion"),
            "mock": {k: ENV.get(k) for k in ("MOCK_LATENCY_MIN_MS", "MOCK_LATENCY_MAX_MS", "MOCK_FAILURE_RATE",
                                             "MOCK_TIMEOUT_RATE")}}


def main(quick: bool) -> None:
    load = {"LOAD_RATE": "100", "LOAD_RAMP": "20s", "LOAD_STEADY": "40s"} if quick else \
           {"LOAD_RATE": "600", "LOAD_RAMP": "1m", "LOAD_STEADY": "5m"}
    seed_drones()
    samples, stop = [], threading.Event()
    start = now_db()
    print(f"Debut du test : {start} UTC ({load})")
    sampler = threading.Thread(target=sample_queue, args=(samples, stop), daemon=True)
    sampler.start()
    k6 = subprocess.run(["docker", "compose", "--profile", "load", "run", "--rm", "k6"], cwd=ROOT,
                        env={**os.environ, **load})
    end = now_db()
    stop.set()
    sampler.join()
    print(f"Fin du test : {end} UTC (k6 code {k6.returncode})")

    window = f"'{start}' AND '{end}'"
    ordered = sql("ordering-db", f"SELECT COUNT(*) FROM service_order_item i JOIN service_order o USING (order_id) "
                                 f"WHERE o.accepted_at BETWEEN {window};")[0][0]
    p95_sql = (ROOT / "load-tests/sql/p95_activation_delay.sql").read_text(encoding="utf-8")
    row = sql("activation-db", f"SET @start='{start}'; SET @end='{end}'; SET @ordered={ordered};\n{p95_sql}")[-1]
    keys = ["ordered_items", "received_items", "active_items", "not_finished_items", "failed_items", "p95_rank",
            "p95_delay_ms", "avg_delay_ms", "max_delay_ms"]
    activation = dict(zip(keys, row))

    summary = json.loads((ROOT / "results/k6-summary.json").read_text(encoding="utf-8"))
    m = summary["metrics"]
    throughput = {
        "iterations": m["iterations"]["values"]["count"],
        "iterationsPerSecondAvg": round(m["iterations"]["values"]["rate"], 1),
        "droppedIterations": m.get("dropped_iterations", {}).get("values", {}).get("count", 0),
        "httpErrorRate": m["http_req_failed"]["values"]["rate"],
        "httpDurationMs": {k: round(v, 1) for k, v in m["http_req_duration"]["values"].items()},
        "thresholdsPassed": k6.returncode == 0,
    }
    result = {"window": {"start": start, "end": end}, "load": load, "environment": environment(),
              "throughput": throughput, "activation": activation, "queueSamples": samples}
    name = f"results/measurement-{'quick' if quick else 'full'}-{start[:19].replace(':', '').replace(' ', 'T')}.json"
    (ROOT / name).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"throughput": throughput, "activation": activation}, indent=2))
    print(f"Resultats : {name}")


if __name__ == "__main__":
    main("--quick" in sys.argv)
