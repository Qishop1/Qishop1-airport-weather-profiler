from __future__ import annotations

from wxprofiler.model import Observation


def classify(obs: Observation) -> str:
    vis_sm = obs.visibility_m / 1609.344 if obs.visibility_m is not None else None
    ceiling = obs.ceiling_ft if obs.ceiling_ft is not None else 99999.0
    if (vis_sm is not None and vis_sm < 1.0) or ceiling < 500:
        return "LIFR"
    if (vis_sm is not None and vis_sm < 3.0) or ceiling < 1000:
        return "IFR"
    if (vis_sm is not None and vis_sm <= 5.0) or ceiling <= 3000:
        return "MVFR"
    return "VFR"
