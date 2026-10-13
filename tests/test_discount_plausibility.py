from src.analysis.analyzer import max_plausible_discount
from src.analysis.scoring import get_battery_health_score, get_condition_score


def test_new_flagship_at_huge_discount_is_implausible():
    # S25 Ultra (2025) for 40k ≈ 94% off: a copy, not a deal
    assert max_plausible_discount(2025, now_year=2026) < 94


def test_old_phone_at_normal_used_price_is_plausible():
    # iPhone 11 (2019) for 55k ≈ 85% off: ordinary used price
    assert max_plausible_discount(2019, now_year=2026) >= 85


def test_cap_applies_to_very_old_phones():
    assert max_plausible_discount(2010, now_year=2026) == 92


def test_screen_stripe_cancels_excellent_condition():

    score, factors = get_condition_score("Состояние отличное, не считая что полоса на экране")
    assert score < 0
    assert any("Screen defect" in f for f in factors)
    assert not any("Excellent" in f for f in factors)


def test_battery_percent_in_title_is_parsed():

    assert get_battery_health_score("", None, title="Iphone 12 128gb 78%")[1] is not None
    assert get_battery_health_score("iPhone 11 Purple 128gb 73% akb", None)[1] is not None
    assert get_battery_health_score("акб 84", None)[1] is not None
    assert "70-79" in get_battery_health_score("оригинал 100% Состояние аккумулятора 78%", None)[1]


def test_unrelated_percent_in_description_is_not_battery():

    assert get_battery_health_score("Сенсор работает на 100%", None) == (0, None)


def test_icloud_lock_is_flagged_but_clean_icloud_is_not():

    assert get_condition_score("Айклаул на блоке, обмен")[0] <= -100
    assert not any("iCloud" in f for f in get_condition_score("icloud чистый")[1])
