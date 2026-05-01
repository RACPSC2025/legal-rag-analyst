# tests/unit/test_numeric_grader.py

import pytest
from src.services.numeric_grader import NumericGrader

class TestNumericGrader:
    
    @pytest.fixture
    def grader(self):
        return NumericGrader()

    def test_parse_number_colombian_format(self, grader):
        # Caso con punto de miles y coma decimal
        assert grader._parse_number("$ 1.250.000,50", "currency") == 1250000.5
        # Caso con comas de miles y punto decimal
        assert grader._parse_number("1,250,000.75", "currency") == 1250000.75

    def test_extract_currency(self, grader):
        text = "La tarifa es de $ 1.500.000 y el recargo de $200,000.50"
        extracted = grader.extract_numbers(text)
        assert 1500000.0 in extracted["currency"]
        assert 200000.5 in extracted["currency"]

    def test_extract_percentages(self, grader):
        text = "Se aplica un 10.5% de IVA y una retención del 3,5 %"
        extracted = grader.extract_numbers(text)
        assert 10.5 in extracted["percentage"]
        assert 3.5 in extracted["percentage"]

    def test_extract_deadlines(self, grader):
        text = "Plazo de 30 días para respuesta, ampliable por 6 meses o 1 año."
        extracted = grader.extract_numbers(text)
        assert 30.0 in extracted["days"]
        assert 6.0 in extracted["months"]
        assert 1.0 in extracted["years"]

    def test_extract_smmlv(self, grader):
        text = "Multa de hasta 500 SMMLV o 10 salarios mínimos."
        extracted = grader.extract_numbers(text)
        assert 500.0 in extracted["smmlv"]
        assert 10.0 in extracted["smmlv"]

    def test_compare_values_with_tolerance(self, grader):
        # Moneda: $1,000.00 vs $1,000.01 (OK)
        is_match, diff = grader.compare_values(1000.0, 1000.01, "currency")
        assert is_match is True
        
        # Porcentaje: 10.0% vs 10.2% (FAIL, tol=0.1)
        is_match, diff = grader.compare_values(10.0, 10.2, "percentage")
        assert is_match is False
        
        # Días: 30 vs 31 (FAIL, tol=0)
        is_match, diff = grader.compare_values(30, 31, "days")
        assert is_match is False

    def test_audit_numbers_detects_hallucination(self, grader):
        context = [
            {"page_content": "La multa será de $ 5.000.000 COP y el plazo de 15 días."}
        ]
        # LLM inventa $6.000.000 y 20 días
        answer = "Debe pagar una multa de $ 6.000.000 en un plazo de 20 días."
        
        discrepancies = grader.audit_numbers(answer, context)
        
        assert len(discrepancies) == 2
        types = [d.data_type for d in discrepancies]
        assert "currency" in types
        assert "days" in types
        
        # Verificar valores esperados vs encontrados
        for d in discrepancies:
            if d.data_type == "currency":
                assert d.expected_value == 5000000.0
                assert d.found_value == 6000000.0
            if d.data_type == "days":
                assert d.expected_value == 15.0
                assert d.found_value == 20.0
