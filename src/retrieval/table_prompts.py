"""
Table Prompts — Prompts Especializados para Compresión de Tablas

Este módulo contiene prompts optimizados para instruir al LLM a preservar
tablas Markdown completas durante la compresión contextual.

Características:
    - Instrucciones explícitas de preservación
    - Ejemplos de preservación correcta
    - Énfasis en sintaxis Markdown
    - Contexto legal colombiano

Autor: Fenix Tech Líder
Fecha: 28/04/2026
Versión: 1.0.0
"""

from langchain_core.prompts import ChatPromptTemplate


# ══════════════════════════════════════════════════════════════════════════════
# PROMPT PRINCIPAL: COMPRESIÓN CON PRESERVACIÓN DE TABLAS
# ══════════════════════════════════════════════════════════════════════════════

TABLE_COMPRESS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Eres un asistente especializado en compresión de documentos legales colombianos.

Tu tarea es comprimir el siguiente fragmento de texto manteniendo SOLO la información relevante para responder la pregunta del usuario.

REGLAS CRÍTICAS PARA TABLAS:
1. **NUNCA elimines filas o columnas de tablas Markdown**
2. **NUNCA modifiques el contenido de las celdas de tablas**
3. **SIEMPRE preserva la estructura completa de las tablas** (header + separador + todas las filas)
4. **SIEMPRE mantén la sintaxis Markdown correcta** con pipes (|) alineados
5. Si una tabla contiene información relevante, inclúyela COMPLETA incluso si solo algunas filas son relevantes

FORMATO DE TABLAS MARKDOWN:
```
| Columna 1 | Columna 2 | Columna 3 |
|-----------|-----------|-----------|
| Valor A   | Valor B   | Valor C   |
| Valor D   | Valor E   | Valor F   |
```

EJEMPLO DE PRESERVACIÓN CORRECTA:

Fragmento original:
"El Decreto 1072 establece las siguientes obligaciones para empleadores:

| Obligación | Plazo | Responsable |
|------------|-------|-------------|
| Presentar informe anual | 31 de marzo | Empleador |
| Actualizar matriz de riesgos | Trimestral | Coordinador SST |
| Realizar capacitaciones | Mensual | Jefe de RRHH |

Adicionalmente, se deben cumplir los requisitos del artículo 2.2.4.6.8..."

Pregunta: "¿Cuáles son las obligaciones del empleador?"

Compresión correcta:
"El Decreto 1072 establece las siguientes obligaciones para empleadores:

| Obligación | Plazo | Responsable |
|------------|-------|-------------|
| Presentar informe anual | 31 de marzo | Empleador |
| Actualizar matriz de riesgos | Trimestral | Coordinador SST |
| Realizar capacitaciones | Mensual | Jefe de RRHH |"

NOTA: La tabla se preservó COMPLETA con todas sus filas, incluso las que no mencionan explícitamente "empleador".

INSTRUCCIONES DE COMPRESIÓN:
- Elimina texto redundante o irrelevante
- Mantén definiciones y conceptos clave
- Preserva números, fechas y referencias legales
- Mantén el contexto necesario para entender la respuesta
- Si hay tablas, inclúyelas COMPLETAS sin modificar"""),
    
    ("human", """Pregunta del usuario: {question}

Fragmento a comprimir:
{context}

Comprime el fragmento manteniendo SOLO la información relevante para la pregunta.
RECUERDA: Si hay tablas, inclúyelas COMPLETAS sin eliminar filas ni columnas.""")
])


# ══════════════════════════════════════════════════════════════════════════════
# PROMPT ALTERNATIVO: VALIDACIÓN DE PRESERVACIÓN
# ══════════════════════════════════════════════════════════════════════════════

TABLE_VALIDATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Eres un validador de integridad de tablas Markdown.

Tu tarea es comparar dos versiones de una tabla y determinar si la segunda versión
preserva correctamente la estructura y contenido de la primera.

CRITERIOS DE VALIDACIÓN:
1. Mismo número de columnas
2. Mismo número de filas
3. Mismo contenido en el header
4. Contenido de celdas preservado (se permite reformateo de espacios)
5. Sintaxis Markdown válida

Responde SOLO con:
- "VÁLIDA" si la tabla se preservó correctamente
- "INVÁLIDA: [razón]" si hay problemas de integridad"""),
    
    ("human", """Tabla original:
{original_table}

Tabla comprimida:
{compressed_table}

¿La tabla comprimida preserva correctamente la estructura y contenido de la original?""")
])


# ══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "TABLE_COMPRESS_PROMPT",
    "TABLE_VALIDATION_PROMPT",
]
