from fincal import storage
from fincal.spending import enrich, load_log
from scripts.make_examples import generate


def test_examples_are_valid_and_current():
    settings = storage.load_settings(storage.settings_path(storage.EXAMPLES_DIR))
    assert settings.validate() == []
    log = enrich(load_log(storage.log_path(storage.EXAMPLES_DIR)), settings)
    assert len(log) > 100
    assert (~log["mapped"]).any(), "examples should include unmapped rows"

    expected_settings, expected_log = generate()
    assert settings == expected_settings, "run scripts/make_examples.py"
    assert len(log) == len(expected_log)
