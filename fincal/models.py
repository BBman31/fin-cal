"""Settings model: everything except the spending log."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

BUCKETS = ("Fixed", "Future", "Flexible")
WEIGHT_TOLERANCE = 0.01


@dataclass
class FixedCost:
    category: str
    amount: float = 0.0
    comment: str = ""


@dataclass
class FlexCategory:
    category: str
    weight: float = 0.0


@dataclass
class OpenClose:
    month: str  # "YYYY-MM"
    open: float | None = None
    close: float | None = None

    @property
    def remaining(self) -> float | None:
        if self.open is None or self.close is None:
            return None
        return self.close - self.open


@dataclass
class Settings:
    currency: str = "DKK"
    income: float = 0.0
    bucket_weights: dict[str, float] = field(
        default_factory=lambda: {"Fixed": 55.0, "Future": 20.0, "Flexible": 25.0}
    )
    fixed_costs: list[FixedCost] = field(default_factory=list)
    flexible_categories: list[FlexCategory] = field(default_factory=list)
    item_categories: dict[str, str] = field(default_factory=dict)
    category_buckets: dict[str, str] = field(default_factory=dict)
    open_close: list[OpenClose] = field(default_factory=list)

    def bucket_budget(self, bucket: str) -> float:
        return self.income * self.bucket_weights.get(bucket, 0.0) / 100

    def flexible_budgets(self) -> dict[str, float]:
        total = self.bucket_budget("Flexible")
        return {c.category: total * c.weight / 100 for c in self.flexible_categories}

    def fixed_planned_total(self) -> float:
        return sum(c.amount for c in self.fixed_costs)

    def validate(self) -> list[str]:
        errors = []
        unknown = set(self.bucket_weights) - set(BUCKETS)
        if unknown:
            errors.append(f"Unknown buckets in weights: {sorted(unknown)}")
        total = sum(self.bucket_weights.values())
        if abs(total - 100) > WEIGHT_TOLERANCE:
            errors.append(f"Bucket weights sum to {total:g}, not 100")
        if self.flexible_categories:
            flex_total = sum(c.weight for c in self.flexible_categories)
            if abs(flex_total - 100) > WEIGHT_TOLERANCE:
                errors.append(f"Flexible category weights sum to {flex_total:g}, not 100")
        bad = {c: b for c, b in self.category_buckets.items() if b not in BUCKETS}
        if bad:
            errors.append(f"Categories mapped to unknown buckets: {bad}")
        if self.income < 0:
            errors.append("Income cannot be negative")
        months = [oc.month for oc in self.open_close]
        if len(months) != len(set(months)):
            errors.append("Open/Close has duplicate months")
        return errors

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Settings:
        data = dict(data or {})
        return cls(
            currency=data.get("currency", "DKK"),
            income=float(data.get("income", 0.0) or 0.0),
            bucket_weights={k: float(v) for k, v in (data.get("bucket_weights") or {}).items()}
            or cls().bucket_weights,
            fixed_costs=[FixedCost(**c) for c in data.get("fixed_costs") or []],
            flexible_categories=[FlexCategory(**c) for c in data.get("flexible_categories") or []],
            item_categories=dict(data.get("item_categories") or {}),
            category_buckets=dict(data.get("category_buckets") or {}),
            open_close=[OpenClose(**oc) for oc in data.get("open_close") or []],
        )
