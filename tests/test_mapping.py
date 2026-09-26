from fincal.mapping import UNMAPPED, Lookup, normalize, resolve_bucket, resolve_category

ITEMS = Lookup.from_dict(
    {
        "Netto": "Food",
        "Netto Billund": "Food",
        "LEGO": "LEGO",
        "LEGO Store BLL ": "LEGO",
        "ABC": "Food",
        "Revolut": "Home",
    }
)
CATEGORIES = Lookup.from_dict({"Food": "Fixed", "LEGO": "Flexible", "Home": "Flexible"})


def test_normalize():
    assert normalize("  LEGO   Store  BLL ") == "lego store bll"
    assert normalize(None) == ""


def test_exact_ignores_case_and_whitespace():
    assert resolve_category("lego store bll", ITEMS) == "LEGO"
    assert resolve_category("NETTO", ITEMS) == "Food"


def test_longest_substring_wins():
    lookup = Lookup.from_dict({"Super": "Food", "Super Brugsen": "Groceries"})
    assert resolve_category("Super Brugsen Vejle", lookup) == "Groceries"
    assert resolve_category("Super Vejle", lookup) == "Food"


def test_substring_match():
    assert resolve_category("Netto Vejle 1234", ITEMS) == "Food"


def test_unmapped():
    assert resolve_category("Some shop", ITEMS) == UNMAPPED
    assert resolve_category(None, ITEMS) == UNMAPPED
    assert resolve_category("", ITEMS) == UNMAPPED


def test_bucket_is_exact_only():
    assert resolve_bucket(" food ", CATEGORIES) == "Fixed"
    assert resolve_bucket("Food court", CATEGORIES) == UNMAPPED


def test_duplicates_first_wins_and_conflicts_reported():
    lookup = Lookup.from_pairs([("Home", "Flexible"), ("home ", "Flexible"), ("HOME", "Fixed")])
    assert lookup.get("home") == "Flexible"
    assert lookup.conflicts == {"home": {"Flexible", "Fixed"}}


def test_blank_rows_skipped():
    lookup = Lookup.from_pairs([("", "Food"), ("Netto", None), ("Netto", "Food")])
    assert lookup.exact == {"netto": "Food"}
