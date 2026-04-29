"""
Tests para TASK-014: Filtros de Metadata Dinámicos
──────────────────────────────────────────────────
Verifica que la extracción de filtros funcione correctamente.

Autor: Fenix Tech Líder + Kiro AI
Fecha: 2026-04-28
"""

import pytest
from src.retrieval.metadata_filters import (
    extract_filters,
    extract_filters_detailed,
    MetadataFilterExtractor,
    ExtractedFilters,
)


class TestMetadataFilterExtractor:
    """Tests para el extractor de filtros de metadata."""
    
    def test_extract_year(self):
        """Test: Extracción de año."""
        filters = extract_filters("Decreto 1082 de 2015")
        assert filters.get('year') == 2015
        
        filters = extract_filters("Ley 100 de 1993")
        assert filters.get('year') == 1993
        
        filters = extract_filters("Resolución 2026")
        assert filters.get('year') == 2026
    
    def test_extract_article(self):
        """Test: Extracción de artículo."""
        filters = extract_filters("¿Qué dice el Artículo 2.2.2.4.11?")
        assert filters.get('article') == "2.2.2.4.11"
        
        filters = extract_filters("Art. 2.2.1.4 establece...")
        assert filters.get('article') == "2.2.1.4"
        
        filters = extract_filters("Según el 2.2.3.2.9.1")
        assert filters.get('article') == "2.2.3.2.9.1"
    
    def test_extract_document_type(self):
        """Test: Extracción de tipo de documento."""
        filters = extract_filters("Decreto 1082 de 2015")
        assert filters.get('document_type') == "decreto"
        
        filters = extract_filters("Ley 100 de 1993")
        assert filters.get('document_type') == "ley"
        
        filters = extract_filters("Resolución 2026")
        assert filters.get('document_type') == "resolucion"
        
        filters = extract_filters("Circular externa")
        assert filters.get('document_type') == "circular"
    
    def test_extract_entity(self):
        """Test: Extracción de entidad."""
        filters = extract_filters("Resolución del Ministerio de Ambiente")
        assert filters.get('entity') is not None
        assert "Ministerio" in filters.get('entity', '')
        
        filters = extract_filters("Concepto de la DIAN")
        assert filters.get('entity') == "DIAN"
        
        filters = extract_filters("Secretaría Distrital de Ambiente")
        assert filters.get('entity') is not None
    
    def test_extract_nit(self):
        """Test: Extracción de NIT."""
        filters = extract_filters("Empresa con NIT 900123456-1")
        assert filters.get('nit') == "900123456-1"
        
        filters = extract_filters("NIT: 800234567")
        assert filters.get('nit') == "800234567"

    def test_extract_norm_number(self):
        """Test: Extracción de número de norma."""
        filters = extract_filters("Decreto 1076 de 2015")
        assert filters.get('resolution_number') == "1076"
        
        filters = extract_filters("Ley 99 de 1993")
        assert filters.get('resolution_number') == "99"
        
        filters = extract_filters("Resolución número 631 de 2015")
        assert filters.get('resolution_number') == "631"
    
    def test_multiple_filters(self):
        """Test: Extracción de múltiples filtros simultáneos."""
        query = "¿Qué dice el Decreto 1082 de 2015 en el Artículo 2.2.2.4.11?"
        filters = extract_filters(query)
        
        assert filters.get('year') == 2015
        assert filters.get('document_type') == "decreto"
        assert filters.get('article') == "2.2.2.4.11"
    
    def test_no_filters(self):
        """Test: Query sin filtros extraíbles."""
        filters = extract_filters("¿Cuáles son los requisitos para pensionarse?")
        assert filters == {}
    
    def test_detailed_extraction(self):
        """Test: Extracción detallada con ExtractedFilters."""
        result = extract_filters_detailed("Decreto 1082 de 2015")
        
        assert isinstance(result, ExtractedFilters)
        assert result.year == 2015
        assert result.document_type == "decreto"
        assert result.has_filters is True
        assert len(result.raw_filters) >= 2
    
    def test_case_insensitive(self):
        """Test: Extracción insensible a mayúsculas/minúsculas."""
        filters1 = extract_filters("DECRETO 1082 DE 2015")
        filters2 = extract_filters("decreto 1082 de 2015")
        filters3 = extract_filters("Decreto 1082 De 2015")
        
        assert filters1.get('document_type') == "decreto"
        assert filters2.get('document_type') == "decreto"
        assert filters3.get('document_type') == "decreto"
    
    def test_article_with_accents(self):
        """Test: Extracción de artículo con tildes."""
        filters1 = extract_filters("Artículo 2.2.2.4.11")
        filters2 = extract_filters("Articulo 2.2.2.4.11")
        
        assert filters1.get('article') == "2.2.2.4.11"
        assert filters2.get('article') == "2.2.2.4.11"
    
    def test_year_boundaries(self):
        """Test: Años en límites válidos."""
        # Año válido mínimo
        filters = extract_filters("Ley de 1900")
        assert filters.get('year') == 1900
        
        # Año válido máximo
        filters = extract_filters("Decreto de 2100")
        assert filters.get('year') == 2100
        
        # Año inválido (fuera de rango)
        filters = extract_filters("Año 1800")
        assert filters.get('year') is None
    
    def test_singleton_pattern(self):
        """Test: Patrón singleton del extractor."""
        from src.retrieval.metadata_filters import get_filter_extractor
        
        extractor1 = get_filter_extractor()
        extractor2 = get_filter_extractor()
        
        assert extractor1 is extractor2


class TestIntegrationWithHybridSearch:
    """Tests de integración con hybrid_search.py."""
    
    def test_filters_applied_automatically(self):
        """Test: Filtros se aplican automáticamente en retrieve."""
        # Este test requiere ChromaDB inicializado
        # Por ahora solo verificamos que la función existe y es callable
        from src.retrieval.hybrid_search import FenixHybridRetriever
        
        assert hasattr(FenixHybridRetriever, 'retrieve')
        assert callable(getattr(FenixHybridRetriever, 'retrieve'))


# ── Tests de casos reales ───────────────────────────────────────────────────

class TestRealWorldQueries:
    """Tests con queries reales del dominio legal colombiano."""
    
    def test_query_concesion_aguas(self):
        """Test: Query sobre concesión de aguas."""
        query = "¿Cuáles son los requisitos del Artículo 2.2.3.2.9.1 del Decreto 1076 de 2015?"
        filters = extract_filters(query)
        
        assert filters.get('year') == 2015
        assert filters.get('document_type') == "decreto"
        assert filters.get('article') == "2.2.3.2.9.1"
    
    def test_query_licencia_ambiental(self):
        """Test: Query sobre licencia ambiental."""
        query = "¿Qué dice la Ley 99 de 1993 sobre licencias ambientales?"
        filters = extract_filters(query)
        
        assert filters.get('year') == 1993
        assert filters.get('document_type') == "ley"
    
    def test_query_tasas_retributivas(self):
        """Test: Query sobre tasas retributivas."""
        query = "Resolución 631 de 2015 sobre tasas retributivas"
        filters = extract_filters(query)
        
        assert filters.get('year') == 2015
        assert filters.get('document_type') == "resolucion"
    
    def test_query_ministerio_ambiente(self):
        """Test: Query con entidad específica."""
        query = "Conceptos del Ministerio de Ambiente sobre vertimientos"
        filters = extract_filters(query)
        
        assert filters.get('entity') is not None
        assert "Ministerio" in filters.get('entity', '')
    
    def test_query_generic(self):
        """Test: Query genérica sin filtros."""
        query = "¿Cómo se tramita una concesión de aguas?"
        filters = extract_filters(query)
        
        # Query genérica no debe extraer filtros
        assert filters == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
