# tests/schemas/test_legal_output.py

import pytest
from pydantic import ValidationError
from src.schemas.legal_output import LegalAnswer, LegalCitation, NumericDiscrepancy


class TestLegalCitation:

    def test_valid_dur_format(self):
        c = LegalCitation(
            article_id="2.2.3.2.9.1",
            source_doc="Decreto 1072 de 2015",
            quote="Las corporaciones autónomas regionales tendrán a su cargo...",
        )
        assert c.is_verified is False
        assert c.relevance_score == 0.0

    def test_valid_complex_formats(self):
        # Parágrafos
        assert LegalCitation(article_id="Parágrafo 1", source_doc="Ley 99", quote="Contenido largo...").article_id == "Parágrafo 1"
        # Secciones
        assert LegalCitation(article_id="Sección III", source_doc="Ley 99", quote="Contenido largo...").article_id == "Sección III"
        # Títulos
        assert LegalCitation(article_id="Título 2", source_doc="Ley 99", quote="Contenido largo...").article_id == "Título 2"

    def test_valid_short_format(self):
        c = LegalCitation(
            article_id="Art. 15",
            source_doc="Ley 99 de 1993",
            quote="El Estado es responsable de la gestión y conservación...",
        )
        assert c.article_id == "Art. 15"

    def test_invalid_article_id_rejected(self):
        with pytest.raises(ValidationError, match="no coincide con ningún formato"):
            LegalCitation(
                article_id="página 10",
                source_doc="Decreto 1072 de 2015",
                quote="Texto de ejemplo suficientemente largo para pasar validación.",
            )

    def test_truncated_quote_rejected(self):
        with pytest.raises(ValidationError, match="truncada"):
            LegalCitation(
                article_id="2.2.1.4",
                source_doc="Decreto 1072 de 2015",
                quote="Las corporaciones [...] tendrán a su cargo.",
            )

    def test_placeholder_source_doc_rejected(self):
        with pytest.raises(ValidationError, match="placeholder"):
            LegalCitation(
                article_id="2.2.1.4",
                source_doc="documento",
                quote="Texto de ejemplo suficientemente largo para pasar validación.",
            )


class TestLegalAnswer:

    def _make_citation(self, verified: bool, score: float = 0.9) -> LegalCitation:
        c = LegalCitation(
            article_id="2.2.1.4",
            source_doc="Decreto 1072 de 2015",
            quote="Las corporaciones autónomas regionales tendrán a su cargo...",
            relevance_score=score,
        )
        c.is_verified = verified
        return c

    def test_confidence_score_computed_from_verified_citations(self):
        answer = LegalAnswer(
            answer="# Respuesta\n\nEl artículo 2.2.1.4 establece..." * 3,
            citations=[
                self._make_citation(verified=True, score=0.9),
                self._make_citation(verified=True, score=0.8),
                self._make_citation(verified=False, score=0.5),
            ],
        )
        assert answer.confidence_score == pytest.approx(0.85, abs=0.01)

    def test_requires_human_review_auto_flagged(self):
        answer = LegalAnswer(
            answer="# Respuesta\n\nEl artículo 2.2.1.4 establece..." * 3,
            citations=[self._make_citation(verified=False)],
        )
        assert answer.requires_human_review is True

    def test_no_review_needed_when_all_verified(self):
        answer = LegalAnswer(
            answer="# Respuesta\n\nEl artículo 2.2.1.4 establece..." * 3,
            citations=[self._make_citation(verified=True)],
        )
        assert answer.requires_human_review is False
        assert answer.confidence_score == pytest.approx(0.9)

    def test_numeric_discrepancy_triggers_review(self):
        answer = LegalAnswer(
            answer="# Respuesta\n\nEl artículo 2.2.1.4 establece..." * 3,
            citations=[self._make_citation(verified=True)],
            numeric_discrepancies=[
                NumericDiscrepancy(
                    field_name="tarifa",
                    expected_value="$1,000,000 COP",
                    found_value="$1,500,000 COP",
                    data_type="currency",
                )
            ],
        )
        assert answer.requires_human_review is True

    def test_verification_summary_format(self):
        citation = self._make_citation(verified=False)
        citation.verification_note = "Texto no coincide (similitud: 72%)"
        answer = LegalAnswer(
            answer="# Respuesta\n\nEl artículo 2.2.1.4 establece..." * 3,
            citations=[citation],
        )
        summary = answer.verification_summary()
        assert summary["verification_passed"] is False
        assert summary["verified_count"] == 0
        assert len(summary["failed_citations"]) == 1
        assert "72%" in summary["failed_citations"][0]["reason"]

    def test_empty_citations_gives_zero_confidence(self):
        answer = LegalAnswer(
            answer="# Respuesta sin citas\n\nTexto genérico..." * 3,
        )
        assert answer.confidence_score == 0.0
        assert answer.requires_human_review is False