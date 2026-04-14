# Herramientas para la Creación de Markdown en el Dominio Legal

El procesamiento de documentos legales es uno de los casos de uso más exigentes debido a la jerarquía de la información (cláusulas, sub-cláusulas, anexos) y a que suelen ser archivos extensos que mezclan texto digital con firmas o sellos escaneados.

---

## 1. Llama Parse: El mejor para la jerarquía legal

Para contratos o términos de servicio complejos, **Llama Parse** suele llevarse la victoria.

*   **Preservación de Estructura:** Al convertir a Markdown, mantiene la numeración de las cláusulas de forma lógica, evitando que el LLM confunda un "Artículo 2" con un simple número de página.
*   **Instrucciones Personalizadas:** Puedes darle una instrucción como: *"Extrae este contrato manteniendo la relación jerárquica de las secciones y asegúrate de no omitir el texto en letra pequeña de los pies de página"*.
*   **Ideal para:** Documentos con muchos niveles de indentación o tablas comparativas de leyes.

## 2. Amazon Textract: El estándar para validez y firmas

Si tus documentos legales son escaneos, notarizaciones o tienen firmas manuscritas, **Textract** es la opción más robusta.

*   **Detección de Firmas:** Puede detectar específicamente dónde hay una firma o un sello, algo vital en auditorías legales.
*   **Queries (Consultas):** Permite hacer preguntas directas al documento antes de pasarlo al RAG, como *"¿Quién es el apoderado legal?"*, extrayendo el dato con alta precisión aunque el documento sea una fotocopia.
*   **Ideal para:** Escrituras públicas, actas constitutivas o contratos antiguos escaneados.

## 3. Docling: Eficiencia en volúmenes masivos

Cuando necesitas procesar miles de páginas de jurisprudencia o archivos de cientos de folios sin que el costo se dispare.

*   **Velocidad de Ingesta:** Es significativamente más rápido que Unstructured al procesar archivos densos de puro texto legal.
*   **Salida Limpia:** Genera un JSON jerárquico que facilita mucho el "chunking" (división del texto) para que el modelo de IA no pierda el hilo en documentos de más de 100 páginas.
*   **Ideal para:** Crear bases de conocimiento de leyes completas o bibliotecas jurídicas.

## 4. Unstructured: Flexibilidad de formatos

Útil si recibes documentos legales en múltiples formatos (correos electrónicos de evidencia .eml, documentos de Word .docx y PDFs).

*   **Estrategia Hi-Res:** Su modelo de detección de elementos identifica títulos y subtítulos legales con gran precisión, permitiendo separar la "paja" (encabezados repetitivos) del contenido sustancial.
*   **Ideal para:** Flujos de trabajo donde la fuente de los documentos legales es heterogénea.

---

## Resumen de Aplicación Legal

| Necesidad Específica | Herramienta Recomendada | Por qué |
| :--- | :--- | :--- |
| Contratos con tablas complejas | **Llama Parse** | Mejor interpretación visual de celdas y filas. |
| Documentos escaneados / Firmas | **Textract** | OCR de nivel industrial y detección de firmas. |
| Análisis de 500+ páginas | **Docling** | Relación óptima entre velocidad y estructura. |
| Múltiples formatos (EML, DOCX) | **Unstructured** | Soporte universal de tipos de archivo. |

---

> [!TIP]
> **Consejo Técnico para RAG Legal**
> Dada la naturaleza de los textos legales, es recomendable usar una estrategia de **"Markdown Chunking"**. Al usar herramientas que devuelven Markdown (como Llama Parse o Docling), puedes dividir el texto basándote en los encabezados (`#`, `##`, `###`). Esto garantiza que una cláusula nunca se corte a la mitad, manteniendo el contexto completo para la IA.

---

## Análisis de Costos y Comparativa Técnica (Abril 2026)

Estimación de costos basada en los precios vigentes a **abril de 2026** y una comparativa de calidad técnica.

### Tabla 1: Costos aproximados por cada 1,000 hojas

*Nota: Los costos de API pueden variar según la región y el volumen, mientras que los de código abierto dependen de tu propia infraestructura (nube o local).*

| Herramienta | Costo por 1,000 hojas (USD) | Modelo de Cobro | Observaciones |
| :--- | :--- | :--- | :--- |
| **Unstructured** | $10.00 - $30.00 | Pago por uso (API) | El modo "Hi-Res" (necesario para legal) es el más costoso. |
| **Docling** | $0.00 | Open Source (Gratis) | Solo pagas el cómputo (CPU/GPU) si lo corres localmente. |
| **Llama Parse** | $0.00 - $3.00 | Freemium | Generalmente ofrece 1,000 páginas/día gratis. El excedente es económico. |
| **Amazon Textract** | $1.50 - $50.00 | Pago por uso (AWS) | $1.50 solo OCR; ~$15.00 con Tablas; ~$50.00 con Formularios. |

### Tabla 2: Comparativa de Calidad y Optimización

Esta tabla califica del 1 al 10 el desempeño específico en el flujo de trabajo para documentos complejos.

| Herramienta | Calidad OCR / Texto | Estructura RAG (Markdown) | Optimización / Velocidad | Costo-Beneficio |
| :--- | :--- | :--- | :--- | :--- |
| **Unstructured** | 9/10 | 8/10 | 7/10 | Media |
| **Docling** | 8/10 | 9/10 | 10/10 | Excelente |
| **Llama Parse** | 9/10 | 10/10 | 8/10 | Alta |
| **Textract** | 10/10 | 7/10 | 9/10 | Media |

---

## Análisis Detallado para Documentos Legales

*   **Llama Parse (La opción inteligente):** Es la que mejor "entiende" la lógica de un contrato. Si tus documentos tienen cláusulas anidadas o tablas comparativas, el resultado que entrega en Markdown es superior para que un LLM (como GPT-4 o Claude) lo procese después sin alucinar. Por 1,000 hojas, es probable que no pagues nada si las procesas en tandas diarias.
*   **Docling (La opción eficiente):** Si tienes una cantidad masiva de documentos legales (ej. 100,000 páginas) y tienes un servidor propio, Docling es la mejor opción. Es extremadamente rápido convirtiendo PDFs a un formato que la IA entiende, y al ser de IBM, tiene un gran manejo de tablas técnicas.
*   **Amazon Textract (La opción de cumplimiento):** Si el documento legal tiene firmas, sellos o está muy mal escaneado (borroso), Textract es el único que garantiza una extracción de caracteres casi perfecta. Sin embargo, es el más caro si activas la detección de formularios y tablas.
*   **Unstructured (La opción versátil):** Es ideal si tus "documentos legales" no son solo PDFs, sino también correos electrónicos de evidencia, archivos de Word o incluso capturas de pantalla de chats, ya que puede unificar todo bajo un mismo esquema de datos.

---

### Recomendación final: 
Para un **MVP de análisis legal**, comienza con **Llama Parse**. Si el volumen crece y el costo se vuelve un problema, migra a **Docling** para procesar todo de forma local y gratuita.