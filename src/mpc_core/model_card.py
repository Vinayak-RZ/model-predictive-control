"""Model card gate for offset-free MPC (C27 / W5.1).

Fields cover what the model predicts, data fitted on, baseline, measured
coverage, where it must not be used, and who owns it. The product runner
refuses MPC without a valid card. Nothing here writes to a plant.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class HeldOutMetrics:
    n_samples: int
    residual_rms: float
    max_abs_error: float

    def __post_init__(self) -> None:
        if self.n_samples < 1:
            raise ValueError("held_out n_samples must be at least 1")
        if self.residual_rms < 0.0:
            raise ValueError("residual_rms must be non-negative")
        if self.max_abs_error < 0.0:
            raise ValueError("max_abs_error must be non-negative")


@dataclass(frozen=True)
class ModelCard:
    """Gate record for an identified linear model.

    ``valid`` requires held-out residual_rms at or under the caller-supplied
    ``max_held_out_rms`` and a non-zero input coefficient. An open threshold
    must not reach this constructor.
    """

    card_id: str
    fit_id: str
    predicts: str
    fitted_on: str
    baseline_train_rms: float
    held_out: HeldOutMetrics
    max_held_out_rms: float
    coverage_note: str
    must_not_use: str
    owner: str
    source: str
    a: float
    b: float
    dt_s: float
    n_train: int
    experiment: str

    def __post_init__(self) -> None:
        if not self.card_id:
            raise ValueError("card_id is required")
        if not self.fit_id:
            raise ValueError("fit_id is required")
        if self.max_held_out_rms < 0.0:
            raise ValueError("max_held_out_rms must be non-negative")
        if self.dt_s <= 0.0:
            raise ValueError("dt_s must be positive")
        if self.n_train < 3:
            raise ValueError("n_train must be at least 3")
        if not self.predicts or not self.fitted_on or not self.owner:
            raise ValueError("predicts, fitted_on and owner are required")
        if not self.must_not_use:
            raise ValueError("must_not_use is required")
        if self.source not in ("plant_sim", "historian"):
            raise ValueError("source must be plant_sim or historian")
        if self.baseline_train_rms < 0.0:
            raise ValueError("baseline_train_rms must be non-negative")

    @property
    def held_out_passed(self) -> bool:
        return self.held_out.residual_rms <= self.max_held_out_rms

    @property
    def valid(self) -> bool:
        return self.held_out_passed and self.b != 0.0

    def as_dict(self) -> dict[str, object]:
        d = asdict(self)
        d["held_out_passed"] = self.held_out_passed
        d["valid"] = self.valid
        return d


def model_card_from_identify(card: object) -> ModelCard:
    """Copy a plant_sim.identify.ModelCard into the process gate record."""
    held = getattr(card, "held_out")
    return ModelCard(
        card_id=str(getattr(card, "card_id")),
        fit_id=str(getattr(card, "fit_id")),
        predicts=str(getattr(card, "predicts")),
        fitted_on=str(getattr(card, "fitted_on")),
        baseline_train_rms=float(getattr(card, "baseline_train_rms")),
        held_out=HeldOutMetrics(
            n_samples=int(getattr(held, "n_samples")),
            residual_rms=float(getattr(held, "residual_rms")),
            max_abs_error=float(getattr(held, "max_abs_error")),
        ),
        max_held_out_rms=float(getattr(card, "max_held_out_rms")),
        coverage_note=str(getattr(card, "coverage_note")),
        must_not_use=str(getattr(card, "must_not_use")),
        owner=str(getattr(card, "owner")),
        source=str(getattr(card, "source")),
        a=float(getattr(card, "a")),
        b=float(getattr(card, "b")),
        dt_s=float(getattr(card, "dt_s")),
        n_train=int(getattr(card, "n_train")),
        experiment=str(getattr(card, "experiment")),
    )
