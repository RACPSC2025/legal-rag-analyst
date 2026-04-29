"""
Metadata Filters — Extracción Dinámica de Filtros para ChromaDB
────────────────────────────────────────────────────────────────
TASK-014: Filtros de Metadata Dinámicos

Objetivo:
  Extraer automáticamente entidades de la consulta (Año, Artículo, Tipo de Norma)
  para aplicar filtros duros en ChromaDB ANTES de la búsqueda vectorial.

Impacto esperado:
  • -30% falsos positivos
  • Evita recuperar artículos de años incorrectos
  • Mejora precisión en búsquedas específicas

Técnicas implementadas:
  1. Extracción de años (1900-2100)
  2. Extracción de artículos (formato DUR: 2.2.2.4.11)
  3. Extracción de tipo de norma (Decreto, Ley, Resolución, etc.)
  4. Extracción de entidades (Ministerios, Corporaciones, etc.)
  5. Extracción de NIT (para búsquedas de empresas)

Uso en hybrid_search.py:
    from src.retrieval.metadata_filters import extract_filters
    
    filters = extract_filters(query)
    docs = vector_store.similarity_search(query, filter=filters)

Autor: Fenix Tech Líder + Kiro AI
Fecha: 2026-04-28
Versión: 1.0.0
"""

from __future__ import annotations

import re
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ── Patrones de Extracción ──────────────────────────────────────────────────

# Años válidos (1900-2100)
_YEAR_PATTERN = re.compile(r'\b(19\d{2}|20\d{2}|21\d{2})\b')

# Artículos en formato DUR (Decreto Único Reglamentario)
# Ejemplos: 2.2.2.4.11, Art. 2.2.1.4, Artículo 2.2.3.2.9.1
_ARTICLE_PATTERNS = [
    re.compile(r'art[íi]culo\s+(\d+(?:\.\d+)+)', re.IGNORECASE),
    re.compile(r'art\.\s*(\d+(?:\.\d+)+)', re.IGNORECASE),
    re.compile(r'\b(\d+(?:\.\d+){3,})\b'),  # Formato numérico puro: al menos 3 puntos (4 niveles)
]

# Tipos de norma
_DOCUMENT_TYPE_PATTERNS = {
    'decreto': re.compile(r'\bdecreto\b', re.IGNORECASE),
    'ley': re.compile(r'\bley\b', re.IGNORECASE),
    'resolucion': re.compile(r'\bresoluci[óo]n\b', re.IGNORECASE),
    'circular': re.compile(r'\bcircular\b', re.IGNORECASE),
    'concepto': re.compile(r'\bconcepto\b', re.IGNORECASE),
    'acuerdo': re.compile(r'\bacuerdo\b', re.IGNORECASE),
    'sentencia': re.compile(r'\bsentencia\b', re.IGNORECASE),
}

# Entidades gubernamentales
_ENTITY_PATTERNS = [
    re.compile(r'ministerio\s+de\s+[\w\s]+', re.IGNORECASE),
    re.compile(r'secretar[íi]a\s+(?:distrital|departamental)\s+de\s+[\w\s]+', re.IGNORECASE),
    re.compile(r'corporaci[óo]n\s+aut[óo]noma\s+regional\s+[\w\s]+', re.IGNORECASE),
    re.compile(r'\b(?:ANLA|SDA|CAR|DIAN|ICBF|SENA)\b'),
]

# NIT (Número de Identificación Tributaria)
_NIT_PATTERN = re.compile(r'NIT\s*[:=]?\s*(\d{6,12}[-\s]?\d?)', re.IGNORECASE)

# Número de norma (ej: Decreto 1076, Ley 99)
_NORM_NUMBER_PATTERN = re.compile(r'(?:decreto|ley|resoluci[óo]n|circular|acuerdo|concepto|sentencia)\s+(?:no\.?|nro\.?|n[úu]mero)?\s*(\d+)', re.IGNORECASE)


# ── Dataclass de Resultado ──────────────────────────────────────────────────

@dataclass
class ExtractedFilters:
    """
    Filtros extraídos de una query legal.
    
    Attributes:
        year: Año extraído (ej: 2015).
        article_id: ID de artículo (ej: "2.2.2.4.11").
        document_type: Tipo de norma (ej: "decreto", "ley").
        entity: Entidad gubernamental (ej: "Ministerio de Ambiente").
        nit: NIT extraído (ej: "900123456-1").
        raw_filters: Diccionario de filtros para ChromaDB.
        has_filters: True si se extrajo al menos un filtro.
    """
    year: Optional[int] = None
    article_id: Optional[str] = None
    document_type: Optional[str] = None
    entity: Optional[str] = None
    nit: Optional[str] = None
    norm_number: Optional[str] = None
    raw_filters: Dict[str, Any] = field(default_factory=dict)
    has_filters: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Construye el diccionario de filtros para ChromaDB.
        
        Returns:
            Diccionario con los filtros extraídos.
        """
        filters = {}
        
        if self.year:
            filters['year'] = self.year
        
        if self.article_id:
            filters['article'] = self.article_id
        
        if self.document_type:
            filters['document_type'] = self.document_type
        
        if self.entity:
            filters['entity'] = self.entity
        
        if self.nit:
            filters['nit'] = self.nit
        
        if self.norm_number:
            filters['resolution_number'] = self.norm_number
        
        if filters:
            logger.info(f"[METADATA_FILTERS] ✅ Filtros extraídos: {filters}")
        else:
            logger.debug("[METADATA_FILTERS] No se extrajeron filtros de la query.")
        
        return filters


# ── Clase Principal ─────────────────────────────────────────────────────────

class MetadataFilterExtractor:
    """
    Extractor de filtros de metadata desde queries legales.
    
    Diseñado para ser stateless y reutilizable. Cada llamada a extract()
    analiza una nueva query sin mantener estado interno.
    
    Principios de diseño:
    - Single Responsibility: Solo extrae filtros, no hace retrieval.
    - Fail-safe: Si no encuentra filtros, retorna diccionario vacío.
    - Logging completo: Cada extracción se registra para trazabilidad.
    """
    
    def __init__(self):
        """Inicializa el extractor."""
        logger.info("[METADATA_FILTER_EXTRACTOR] Inicializado.")
    
    def extract(self, query: str) -> ExtractedFilters:
        """
        Extrae filtros de metadata desde una query legal.
        
        Proceso:
        1. Extrae año (si existe).
        2. Extrae artículo (si existe).
        3. Extrae tipo de documento (si existe).
        4. Extrae entidad (si existe).
        5. Extrae NIT (si existe).
        6. Construye diccionario de filtros para ChromaDB.
        
        Args:
            query: Query del usuario en lenguaje natural.
            
        Returns:
            ExtractedFilters con todos los filtros encontrados.
            
        Example:
            >>> extractor = MetadataFilterExtractor()
            >>> filters = extractor.extract("¿Qué dice el Decreto 1082 de 2015?")
            >>> print(filters.raw_filters)
            {'year': 2015, 'document_type': 'decreto'}
        """
        logger.debug(f"[METADATA_FILTERS] Analizando query: '{query[:80]}...'")
        
        result = ExtractedFilters()
        
        # 1. Extraer año
        result.year = self._extract_year(query)
        
        # 2. Extraer artículo
        result.article_id = self._extract_article(query)
        
        # 3. Extraer tipo de documento
        result.document_type = self._extract_document_type(query)
        
        # 4. Extraer entidad
        result.entity = self._extract_entity(query)
        
        # 5. Extraer NIT
        result.nit = self._extract_nit(query)
        
        # 6. Extraer número de norma
        result.norm_number = self._extract_norm_number(query)
        
        # 7. Construir diccionario de filtros
        result.raw_filters = result.to_dict()
        result.has_filters = len(result.raw_filters) > 0
        
        return result
    
    # ── Métodos privados de extracción ───────────────────────────────────────
    
    def _extract_year(self, query: str) -> Optional[int]:
        """
        Extrae el año de la query.
        
        Args:
            query: Query del usuario.
            
        Returns:
            Año como entero o None si no se encuentra.
            
        Example:
            >>> _extract_year("Decreto 1082 de 2015")
            2015
        """
        match = _YEAR_PATTERN.search(query)
        if match:
            year = int(match.group(1))
            logger.debug(f"[YEAR] Extraído: {year}")
            return year
        return None
    
    def _extract_article(self, query: str) -> Optional[str]:
        """
        Extrae el ID de artículo de la query.
        
        Soporta múltiples formatos:
        - "Artículo 2.2.2.4.11"
        - "Art. 2.2.1.4"
        - "2.2.3.2.9.1"
        
        Args:
            query: Query del usuario.
            
        Returns:
            ID de artículo como string o None si no se encuentra.
            
        Example:
            >>> _extract_article("¿Qué dice el Artículo 2.2.2.4.11?")
            "2.2.2.4.11"
        """
        for pattern in _ARTICLE_PATTERNS:
            match = pattern.search(query)
            if match:
                article_id = match.group(1).strip()
                logger.debug(f"[ARTICLE] Extraído: {article_id}")
                return article_id
        return None
    
    def _extract_document_type(self, query: str) -> Optional[str]:
        """
        Extrae el tipo de documento de la query.
        
        Tipos soportados:
        - decreto
        - ley
        - resolucion
        - circular
        - concepto
        - acuerdo
        - sentencia
        
        Args:
            query: Query del usuario.
            
        Returns:
            Tipo de documento como string o None si no se encuentra.
            
        Example:
            >>> _extract_document_type("Decreto 1082 de 2015")
            "decreto"
        """
        for doc_type, pattern in _DOCUMENT_TYPE_PATTERNS.items():
            if pattern.search(query):
                logger.debug(f"[DOCUMENT_TYPE] Extraído: {doc_type}")
                return doc_type
        return None
    
    def _extract_entity(self, query: str) -> Optional[str]:
        """
        Extrae la entidad gubernamental de la query.
        
        Entidades soportadas:
        - Ministerios
        - Secretarías
        - Corporaciones Autónomas Regionales
        - Siglas (ANLA, SDA, CAR, DIAN, ICBF, SENA)
        
        Args:
            query: Query del usuario.
            
        Returns:
            Nombre de entidad como string o None si no se encuentra.
            
        Example:
            >>> _extract_entity("Resolución del Ministerio de Ambiente")
            "Ministerio de Ambiente"
        """
        for pattern in _ENTITY_PATTERNS:
            match = pattern.search(query)
            if match:
                entity = match.group(0).strip()
                logger.debug(f"[ENTITY] Extraído: {entity}")
                return entity
        return None
    
    def _extract_nit(self, query: str) -> Optional[str]:
        """
        Extrae el NIT de la query.
        
        Args:
            query: Query del usuario.
            
        Returns:
            NIT como string o None si no se encuentra.
            
        Example:
            >>> _extract_nit("Empresa con NIT 900123456-1")
            "900123456-1"
        """
        match = _NIT_PATTERN.search(query)
        if match:
            nit = match.group(1).strip()
            logger.debug(f"[NIT] Extraído: {nit}")
            return nit
        return None

    def _extract_norm_number(self, query: str) -> Optional[str]:
        """Extrae el número de la norma (ej: 1076 de Decreto 1076)."""
        match = _NORM_NUMBER_PATTERN.search(query)
        if match:
            num = match.group(1).strip()
            logger.debug(f"[NORM_NUMBER] Extraído: {num}")
            return num
        return None


# ── Singleton y funciones de conveniencia ───────────────────────────────────

_extractor: Optional[MetadataFilterExtractor] = None


def get_filter_extractor() -> MetadataFilterExtractor:
    """
    Retorna una instancia singleton del MetadataFilterExtractor.
    
    Returns:
        Instancia singleton de MetadataFilterExtractor.
    """
    global _extractor
    if _extractor is None:
        _extractor = MetadataFilterExtractor()
    return _extractor


def extract_filters(query: str) -> Dict[str, Any]:
    """
    Shortcut funcional para extraer filtros de una query.
    
    Esta es la función principal que debes usar en hybrid_search.py.
    
    Args:
        query: Query del usuario en lenguaje natural.
        
    Returns:
        Diccionario de filtros para ChromaDB. Vacío si no se encontraron filtros.
        
    Example:
        >>> from src.retrieval.metadata_filters import extract_filters
        >>> filters = extract_filters("¿Qué dice el Decreto 1082 de 2015?")
        >>> print(filters)
        {'year': 2015, 'document_type': 'decreto'}
        
        >>> # Uso en retrieval
        >>> docs = vector_store.similarity_search(query, filter=filters)
    """
    extracted = get_filter_extractor().extract(query)
    return extracted.raw_filters


def extract_filters_detailed(query: str) -> ExtractedFilters:
    """
    Extrae filtros con información detallada.
    
    Útil para debugging o cuando necesitas acceso a todos los campos extraídos.
    
    Args:
        query: Query del usuario.
        
    Returns:
        ExtractedFilters con todos los campos y metadata.
        
    Example:
        >>> from src.retrieval.metadata_filters import extract_filters_detailed
        >>> result = extract_filters_detailed("Decreto 1082 de 2015")
        >>> print(result.year)  # 2015
        >>> print(result.document_type)  # "decreto"
        >>> print(result.has_filters)  # True
    """
    return get_filter_extractor().extract(query)


# ── Exports ─────────────────────────────────────────────────────────────────

__all__ = [
    "MetadataFilterExtractor",
    "ExtractedFilters",
    "extract_filters",
    "extract_filters_detailed",
    "get_filter_extractor",
]
