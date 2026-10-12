from decimal import Decimal
from fastapi.testclient import TestClient
from app.main import app
from app.pricing import CalculationInput, calculate

client = TestClient(app)

def sample(**changes):
    return CalculationInput(**(dict(quantity=50, unit_cost='80', unit_price='110', stock=50, lead_days=5) | changes))

def test_correct_margin():
    result = calculate(sample())
    assert result.total == Decimal('5500.00')
    assert result.cost == Decimal('4000.00')
    assert abs(result.margin - Decimal('0.272727272727')) < Decimal('.000000001')
    assert result.checks_passed

def test_margin_is_not_markup():
    assert not calculate(sample(unit_price='96')).checks_passed

def test_unknown_stock_and_delivery_block():
    result = calculate(sample(stock=None, lead_days=None))
    assert len(result.issues) == 2
    assert not result.checks_passed

def test_policy_stock_and_delivery_failures():
    result = calculate(sample(discount='.2', stock=1, lead_days=10))
    assert len(result.issues) == 4

def test_boundary_margin_allowed():
    assert calculate(sample(unit_price='100')).checks_passed

def test_rounding_to_zero_does_not_divide_by_zero():
    result = calculate(sample(quantity=1, unit_cost='0', unit_price='.0001'))
    assert result.margin is None
    assert not result.checks_passed

def test_half_up():
    assert calculate(sample(quantity=1, unit_price='100.005')).total == Decimal('100.01')

def test_invalid_input():
    for change in ({'quantity': 0}, {'unit_price': '-1'}, {'discount': '1'}, {'unit_cost': 'NaN'}):
        payload = dict(quantity=1, unit_cost='1', unit_price='2') | change
        assert client.post('/api/demo/calculate', json=payload).status_code == 422

def test_decimal_serialization():
    response = client.post('/api/demo/calculate', json=dict(quantity=2, unit_cost='1', unit_price='2', stock=2, lead_days=1))
    assert response.status_code == 200
    assert response.json()['total'] == '4.00'

def test_liveness_and_missing_database(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    assert client.get('/api/health').status_code == 200
    assert client.get('/api/ready').status_code == 503
