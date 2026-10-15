"""Bounded checks of actual scrape/query and provisioned dashboard APIs."""

import json
from pathlib import Path

from recovery_lab.contracts import call
from recovery_lab.experiment import wait_until

query = "/api/v1/query?query=sum(lab_scenarios_total)"
metrics = wait_until(lambda: call("http://127.0.0.1:19090", query)["data"]["result"], budget=30)
assert float(metrics[0]["value"][1]) >= 10
dashboard = wait_until(
    lambda: call("http://127.0.0.1:13000", "/api/dashboards/uid/lab-recovery"), budget=30
)
assert dashboard["dashboard"]["title"] == "Agent Failure and Recovery Lab"
assert len(dashboard["dashboard"]["panels"]) == 5
assert dashboard["meta"]["provisioned"] is True
result = {
    "prometheus_queried": True,
    "scraped_scenario_count": float(metrics[0]["value"][1]),
    "grafana_provisioned_dashboard": True,
    "dashboard_panels": 5,
}
Path(".lab").mkdir(exist_ok=True)
Path(".lab/observability.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result))
