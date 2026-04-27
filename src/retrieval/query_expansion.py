"""
Query Expansion — HyDE + Multi-Query para RAG Legal Colombiano
──────────────────────────────────────────────────────────────
Técnicas implementadas:
  1. HyDE (Hypothetical Document Embeddings): genera una respuesta hipotética
     legal antes de buscar. El embedding de esa respuesta es más cercano al
     espacio de los documentos que el embedding de la pregunta original.

  2. Multi-Query: descompone preguntas complejas en 3–5 sub-queries
     ortogonales para máxima cobertura en el vector space.

  3. Query Normalization: limpia y normaliza la pregunta para BM25
     (elimina stopwords legales irrelevantes, normaliza tildes, etc.)

Razones de este módulo:
  • Mejora recall en 30-40% según benchmarks RAG enterprise.
  • Maneja queries ambiguas o con terminología variada.
  • Maximiza cobertura del espacio vectorial con múltiples representaciones.

Uso en nodes.py:
    from src.retrieval.query_expansion import expand_query
    expanded = expand_query(state.question)
    # expanded.queries → lista de queries para multi-retrieval
    # expanded.hyde_doc → documento hipotético para embedding
    # expanded.normalized → query limpia para BM25

Autor: Fenix Tech Líder
Fecha: 2026-04-26
Versión: 1.0.0
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from src.config import get_llm

logger = logging.getLogger(__name__)

# ── Stopwords legales que no aportan al retrieval ───────────────────────────
# Estas palabras son comunes en queries pero no ayudan a discriminar documentos
_LEGAL_STOPWORDS = frozenset({
    "el", "la", "los", "las", "un", "una", "unos", "unas",
    "de", "del", "al", "en", "con", "por", "para", "que",
    "cuál", "cuáles", "qué", "cómo", "cuándo", "dónde",
    "es", "son", "está", "están", "hay", "tiene", "tienen",
    "me", "puede", "puedo", "favor", "diga", "dime",
    "información", "sobre", "acerca", "respecto",
})

# ── Prompts optimizados para normativa colombiana ────────────────────────────

_HYDE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """Eres un experto en normativa colombiana. Tu tarea es generar un FRAGMENTO DE DOCUMENTO LEGAL
hipotético que respondería directamente la pregunta del usuario.

REGLAS ESTRICTAS:
1. Escribe como si fuera un artículo o sección de una norma colombiana real.
2. Incluye lenguaje técnico-jurídico, referencias a artículos, cifras y tablas si aplica.
3. Máximo 300 palabras — denso y específico, no genérico.
4. No aclares que es hipotético, escríbelo como norma real.
5. Usa el formato: "Artículo X. [Título]. [Contenido]..."
6. Si la pregunta menciona un artículo específico, úsalo en tu respuesta.

EJEMPLOS DE FORMATO:
- "ARTÍCULO 2.2.1.4. Requisitos para concesión de aguas. Para obtener..."
- "PARÁGRAFO 1. Los plazos establecidos en el presente artículo..."
- "Tabla 1. Tarifas aplicables según el tipo de usuario..."
""",
    ),
    ("human", "Pregunta: {question}\n\nFragmento normativo hipotético:"),
])

_MULTI_QUERY_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """Eres un analista legal colombiano experto en recuperación de información normativa.

Tu tarea: dado una consulta legal, genera exactamente {n_queries} versiones alternativas
de la misma pregunta que cubran ángulos distintos para maximizar la recuperación de documentos.

REGLAS ESTRICTAS:
1. Cada versión debe ser DIFERENTE en enfoque: terminología, jerarquía normativa, entidad, etc.
2. Incluye variantes con: número de artículo si lo hay, sinónimos legales, norma relacionada.
3. Una variante debe ser muy específica (artículo exacto), otra más general (tema amplio).
4. Devuelve SOLO las preguntas, una por línea, sin numeración ni bullets.
5. No repitas la pregunta original tal cual.
6. Usa terminología legal colombiana (Decreto, Resolución, Concepto, etc.)

EJEMPLOS:
Pregunta original: "¿Cuáles son los requisitos para pensionarse?"
Variantes:
- ¿Qué condiciones establece la Ley 100 de 1993 para acceder a la pensión de vejez?
- ¿Cuántas semanas de cotización se necesitan para pensión en Colombia?
- ¿Qué requisitos de edad y tiempo cotizado exige el sistema pensional colombiano?
""",
    ),
    ("human", "Consulta original: {question}\n\nVariantes:"),
])

# ── Dataclass de resultado ────────────────────────────────────────────────────

@dataclass
class ExpandedQuery:
    """
    Resultado de la expansión de una query legal.
    
    Attributes:
        original: Query original del usuario.
        normalized: Query normalizada para BM25 (sin stopwords).
        hyde_doc: Documento hipotético generado para embedding.
        queries: Lista de variantes de la query (multi-query).
        all_queries: Lista combinada: original + variantes (sin duplicados).
    """
    original: str
    normalized: str                        # Para BM25
    hyde_doc: str = ""                     # Documento hipotético para embedding
    queries: List[str] = field(default_factory=list)  # Multi-query variants
    all_queries: List[str] = field(default_factory=list)  # original + variants

    def __post_init__(self):
        """
        Post-inicialización: combina original + variantes eliminando duplicados.
        Garantiza que la query original siempre esté primera en all_queries.
        """
        seen = {self.original}
        combined = [self.original]
        for q in self.queries:
            q_stripped = q.strip()
            if q_stripped and q_stripped not in seen:
                seen.add(q_stripped)
                combined.append(q_stripped)
        self.all_queries = combined
        
        logger.info(
            f"[QUERY_EXPANSION] Query expandida: "
            f"1 original + {len(self.queries)} variantes + "
            f"{'HyDE' if self.hyde_doc else 'sin HyDE'}"
        )


# ── Clase principal ──────────────────────────────────────────────────────────

class QueryExpander:
    """
    Expande queries legales con HyDE y Multi-Query.
    
    Diseñado para ser stateless y reutilizable. Cada llamada a expand()
    genera un nuevo ExpandedQuery sin mantener estado interno.
    
    Principios de diseño:
    - Single Responsibility: Solo expande queries, no hace retrieval.
    - Fail-safe: Si HyDE o Multi-Query fallan, retorna la query original.
    - Logging completo: Cada paso se registra para trazabilidad.
    
    Args:
        n_multi_queries: Número de variantes a generar (default: 3).
        use_hyde: Si True, genera documento hipotético (default: True).
    """

    def __init__(self, n_multi_queries: int = 3, use_hyde: bool = True):
        """
        Inicializa el expander con configuración.
        
        Args:
            n_multi_queries: Número de variantes de query a generar (1-5 recomendado).
            use_hyde: Si True, genera documento hipotético con LLM.
        """
        self.n_multi_queries = max(1, min(n_multi_queries, 5))  # Límite 1-5
        self.use_hyde = use_hyde
        logger.info(
            f"[QUERY_EXPANDER] Inicializado: "
            f"n_queries={self.n_multi_queries}, hyde={'ON' if use_hyde else 'OFF'}"
        )

    def expand(self, question: str) -> ExpandedQuery:
        """
        Expande la pregunta original en múltiples representaciones.
        
        Proceso:
        1. Normaliza la query para BM25 (elimina stopwords).
        2. Genera documento hipotético con HyDE (si está habilitado).
        3. Genera variantes de la query con Multi-Query.
        4. Retorna ExpandedQuery con todas las representaciones.
        
        Args:
            question: Pregunta del usuario en lenguaje natural.
            
        Returns:
            ExpandedQuery con hyde_doc, queries alternativas y all_queries.
            
        Raises:
            No lanza excepciones. Si algo falla, retorna query original.
        """
        logger.info(f"[QUERY_EXPANSION] Expandiendo query: '{question[:80]}...'")
        
        # Paso 1: Normalización para BM25
        normalized = self._normalize(question)
        logger.debug(f"[NORMALIZE] '{question}' → '{normalized}'")
        
        hyde_doc = ""
        multi_queries: List[str] = []

        # Obtener LLM para generación (usa modelo configurado en settings)
        llm = get_llm(task="generate")  # Usamos modelo potente para calidad

        # Paso 2: HyDE - Generación de documento hipotético
        if self.use_hyde:
            try:
                logger.info("[HYDE] Generando documento hipotético...")
                hyde_chain = _HYDE_PROMPT | llm | StrOutputParser()
                hyde_doc = hyde_chain.invoke({"question": question}).strip()
                logger.info(
                    f"[HYDE] ✅ Documento generado ({len(hyde_doc)} chars): "
                    f"'{hyde_doc[:100]}...'"
                )
            except Exception as e:
                logger.warning(f"[HYDE] ⚠️ Error generando documento hipotético: {e}")
                logger.warning("[HYDE] Continuando sin HyDE...")

        # Paso 3: Multi-Query - Generación de variantes
        try:
            logger.info(f"[MULTI-QUERY] Generando {self.n_multi_queries} variantes...")
            mq_chain = _MULTI_QUERY_PROMPT | llm | StrOutputParser()
            raw = mq_chain.invoke({
                "question": question,
                "n_queries": self.n_multi_queries,
            })
            multi_queries = self._parse_queries(raw)
            logger.info(
                f"[MULTI-QUERY] ✅ {len(multi_queries)} variantes generadas:"
            )
            for i, q in enumerate(multi_queries, 1):
                logger.info(f"  {i}. '{q[:80]}...'")
        except Exception as e:
            logger.warning(f"[MULTI-QUERY] ⚠️ Error generando variantes: {e}")
            logger.warning("[MULTI-QUERY] Continuando solo con query original...")

        # Construir resultado
        result = ExpandedQuery(
            original=question,
            normalized=normalized,
            hyde_doc=hyde_doc,
            queries=multi_queries,
        )
        
        logger.info(
            f"[QUERY_EXPANSION] ✅ Expansión completada: "
            f"{len(result.all_queries)} queries totales"
        )
        
        return result

    # ── Métodos privados de procesamiento ─────────────────────────────────────

    def _normalize(self, text: str) -> str:
        """
        Normaliza la query para BM25.
        
        Proceso:
        1. Convierte a minúsculas.
        2. Elimina puntuación excepto puntos y guiones en números (2.2.1.4).
        3. Elimina stopwords legales irrelevantes.
        4. Normaliza espacios múltiples.
        
        Args:
            text: Query original.
            
        Returns:
            Query normalizada para BM25.
            
        Example:
            >>> _normalize("¿Cuál es el Artículo 2.2.1.4 de la Ley?")
            "artículo 2.2.1.4 ley"
        """
        # Paso 1: Lowercase
        t = text.lower()
        
        # Paso 2: Preservar números con puntos (artículos DUR-style: 2.2.1.4)
        # Eliminar puntuación excepto . y - en contexto numérico
        t = re.sub(r"[^\w\s\.\-]", " ", t)
        
        # Paso 3: Eliminar stopwords legales
        tokens = [w for w in t.split() if w not in _LEGAL_STOPWORDS]
        
        # Paso 4: Normalizar espacios
        normalized = " ".join(tokens)
        
        return normalized

    def _parse_queries(self, raw: str) -> List[str]:
        """
        Parsea las variantes generadas por el LLM.
        
        El LLM puede devolver las queries con numeración, bullets o formato libre.
        Este método limpia y extrae solo las queries válidas.
        
        Args:
            raw: Texto crudo del LLM con las variantes.
            
        Returns:
            Lista de queries limpias (máximo n_multi_queries).
            
        Example:
            >>> _parse_queries("1. ¿Query 1?\n2. ¿Query 2?")
            ["¿Query 1?", "¿Query 2?"]
        """
        lines = raw.strip().split("\n")
        queries: List[str] = []
        
        for line in lines:
            # Limpiar numeración o bullets si el LLM los incluyó
            # Patrones: "1. ", "- ", "• ", "* "
            clean = re.sub(r"^[\d\.\-\*\•]\s*", "", line).strip()
            
            # Validar que sea una query válida (mínimo 10 caracteres)
            if clean and len(clean) > 10:
                queries.append(clean)
        
        # Retornar máximo n_multi_queries variantes
        return queries[: self.n_multi_queries]


# ── Singleton y funciones de conveniencia ────────────────────────────────────

_expander: Optional[QueryExpander] = None


def get_query_expander(n_queries: int = 3, use_hyde: bool = True) -> QueryExpander:
    """
    Retorna una instancia singleton del QueryExpander.
    
    Evita crear múltiples instancias innecesarias. La configuración
    se establece en la primera llamada y se reutiliza.
    
    Args:
        n_queries: Número de variantes a generar.
        use_hyde: Si True, habilita HyDE.
        
    Returns:
        Instancia singleton de QueryExpander.
    """
    global _expander
    if _expander is None:
        _expander = QueryExpander(n_multi_queries=n_queries, use_hyde=use_hyde)
    return _expander


def expand_query(
    question: str, 
    n_queries: int = 3, 
    use_hyde: bool = True
) -> ExpandedQuery:
    """
    Shortcut funcional para expandir una query.
    
    Esta es la función principal que debes usar en nodes.py.
    
    Args:
        question: Pregunta del usuario.
        n_queries: Número de variantes a generar (default: 3).
        use_hyde: Si True, genera documento hipotético (default: True).
        
    Returns:
        ExpandedQuery con todas las representaciones de la query.
        
    Example:
        >>> from src.retrieval.query_expansion import expand_query
        >>> expanded = expand_query("¿Cuáles son los requisitos?")
        >>> print(expanded.hyde_doc)  # Documento hipotético
        >>> print(expanded.all_queries)  # [original, variante1, variante2, ...]
    """
    return get_query_expander(n_queries=n_queries, use_hyde=use_hyde).expand(question)


# ── Exports ──────────────────────────────────────────────────────────────────

__all__ = [
    "QueryExpander",
    "ExpandedQuery",
    "expand_query",
    "get_query_expander",
]
