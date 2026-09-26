import pytest

from fincal import storage
from fincal.models import FixedCost, FlexCategory, OpenClose, Settings


def make_settings() -> Settings:
    return Settings(
        income=30000,
        fixed_costs=[FixedCost("Rent", 9000, "flat"), FixedCost("Insurance", 500)],
        flexible_categories=[FlexCategory("Clothes", 60), FlexCategory("Travel", 40)],
        item_categories={"Netto": "Food", "Boozt": "Clothes"},
        category_buckets={"Food": "Fixed", "Clothes": "Flexible"},
        open_close=[OpenClose("2026-01", 1000, 4000), OpenClose("2026-02", 4000, None)],
    )


def test_round_trip(tmp_path):
    path = tmp_path / "settings.yaml"
    original = make_settings()
    storage.save_settings(original, path)
    assert storage.load_settings(path) == original


def test_budgets():
    s = make_settings()
    assert s.bucket_budget("Fixed") == 16500
    assert s.bucket_budget("Flexible") == 7500
    assert s.flexible_budgets() == {"Clothes": 4500, "Travel": 3000}
    assert s.fixed_planned_total() == 9500
    assert s.open_close[0].remaining == 3000
    assert s.open_close[1].remaining is None


def test_invalid_weights_block_save(tmp_path):
    s = make_settings()
    s.bucket_weights["Fixed"] = 60
    assert any("Bucket weights sum to 105" in e for e in s.validate())
    with pytest.raises(storage.SettingsError):
        storage.save_settings(s, tmp_path / "settings.yaml")
    assert not (tmp_path / "settings.yaml").exists()


def test_invalid_bucket_and_duplicate_month():
    s = make_settings()
    s.category_buckets["Food"] = "Fun"
    s.open_close.append(OpenClose("2026-01"))
    errors = s.validate()
    assert any("unknown buckets" in e for e in errors)
    assert any("duplicate months" in e for e in errors)


def test_missing_file_gives_defaults(tmp_path):
    assert storage.load_settings(tmp_path / "nope.yaml") == Settings()


def test_data_dir_falls_back_to_examples(tmp_path, monkeypatch):
    monkeypatch.setenv("FINCAL_DATA_DIR", str(tmp_path))
    assert storage.is_example_data(storage.data_dir())
    (tmp_path / "settings.yaml").write_text("income: 1\n")
    assert storage.data_dir() == tmp_path
