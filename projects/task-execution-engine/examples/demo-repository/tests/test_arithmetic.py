def test_invoice_total():
    assert sum([125, 250, 75]) == 450


def test_discount():
    assert 200 * 90 // 100 == 180
