"""Write the synthetic value-model result JSON."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from flowmining.value_model import calculate_value_model


def main() -> None:
    output = ROOT / "analysis" / "results" / "value_model.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    result = calculate_value_model()
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=True, allow_nan=False)
        handle.write("\n")
    print(f"payback_months={result['ramp']['payback_months']:.6f}")
    print(f"npv_36_months_usd={result['ramp']['npv_36_months_usd']:.2f}")
    for row in result["sensitivity"]:
        print(f"adoption={row['adoption']:.0%} hours={row['hours_per_year']:.2f} value_usd={row['gross_value_usd_per_year']:.2f} payback_months={row['steady_state_payback_months']:.4f}")


if __name__ == "__main__":
    main()
