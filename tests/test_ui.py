import shutil

import pytest
from streamlit.testing.v1 import AppTest

from fincal import storage


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """A writable copy of the example data."""
    shutil.copytree(storage.EXAMPLES_DIR, tmp_path, dirs_exist_ok=True)
    monkeypatch.setenv("FINCAL_DATA_DIR", str(tmp_path))
    return tmp_path


def run_page(page: str) -> AppTest:
    at = AppTest.from_file(str(storage.PROJECT_ROOT / "app.py"), default_timeout=30)
    at.run()
    at.switch_page(page)
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    return at


def test_example_mode_is_read_only(monkeypatch, tmp_path):
    monkeypatch.setenv("FINCAL_DATA_DIR", str(tmp_path / "missing"))
    at = run_page("pages/budget_setup.py")
    save = next(b for b in at.button if b.label == "Save")
    assert save.disabled


def test_budget_setup_saves_income(data_dir):
    at = run_page("pages/budget_setup.py")
    assert at.metric[0].value == "17 600 DKK"
    at.number_input[0].set_value(40000).run()
    assert at.metric[0].value == "22 000 DKK"
    next(b for b in at.button if b.label == "Save").click().run()
    assert storage.load_settings(data_dir / "settings.yaml").income == 40000


def test_mappings_page_renders_with_hit_counts(data_dir):
    at = run_page("pages/mappings.py")
    assert at.title[0].value == "Mappings"
    assert not at.error
    save = next(b for b in at.button if b.label == "Save mappings")
    assert save.disabled  # nothing changed yet


def test_open_close_start_next_month(data_dir):
    at = run_page("pages/open_close.py")
    start = next(b for b in at.button if b.label.startswith("Start"))
    assert start.label == "Start Oct 2026"
    start.click().run()
    assert not at.exception
    oc = storage.load_settings(data_dir / "settings.yaml").open_close
    assert oc[-1].month == "2026-10"
    assert oc[-1].open is None  # Sep has no close yet

    settings = storage.load_settings(data_dir / "settings.yaml")
    settings.open_close[-1].close = 1234.5
    storage.save_settings(settings, data_dir / "settings.yaml")
    at = run_page("pages/open_close.py")
    next(b for b in at.button if b.label == "Start Nov 2026").click().run()
    oc = storage.load_settings(data_dir / "settings.yaml").open_close
    assert (oc[-1].month, oc[-1].open) == ("2026-11", 1234.5)


def test_spending_log_filters_and_unmapped(data_dir):
    at = run_page("pages/spending_log.py")
    assert at.title[0].value == "Spending Log"
    assert "unmapped item" in at.expander[0].label
    rows_latest = int(at.metric[0].value)
    at.multiselect[0].set_value([]).run()  # all months
    assert int(at.metric[0].value.replace(" ", "")) > rows_latest
    at.text_input[0].set_value("netto").run()
    assert not at.exception
    add = next(b for b in at.button if b.label.startswith("Add"))
    assert add.disabled  # no category picked yet


def test_dashboard_renders_every_month(data_dir):
    at = run_page("pages/dashboard.py")
    assert at.title[0].value == "Dashboard"
    assert [m.label for m in at.metric][:2] == ["Spent", "Left to spend"]
    for month in at.selectbox[0].options:
        at.selectbox[0].select(month).run()
        assert not at.exception, month


def test_dashboard_empty_log(data_dir):
    (data_dir / "spending_log.xlsx").unlink()
    at = run_page("pages/dashboard.py")
    assert "No spending yet" in at.info[0].value
