"""
Numeric Grader Service — Fénix Legal v2.5
────────────────────────────────────────────────────────────
Servicio especializado en la validación de integridad numérica.
Detecta y compara cifras, fechas, plazos y porcentajes entre
la respuesta generada y las fuentes originales (tablas/texto).
"""

import re
import logging
from typing import List, Dict, Any, Union, Optional, Tuple
from pydantic import BaseModel

from src.schemas.legal_output import NumericDiscrepancy

logger = logging.getLogger(__name__)

class NumericGrader:
    """
    Motor de validación numérica para el Analista Jurídico.
    Asegura que los datos cuantitativos no sufran alucinaciones.
    """
    
    # Patrones para extracción de datos numéricos
    PATTERNS = {
        "currency": r'\$\s?(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)',
        "percentage": r'(\d+(?:[.,]\d+)?)\s?%',
        "days": r'(\d+)\s?(?:días|dias)',
        "months": r'(\d+)\s?(?:meses|mes)',
        "years": r'(\d+)\s?(?:años|año|anual)',
        "smmlv": r'(\d+(?:[.,]\d+)?)\s?(?:SMMLV|salarios mínimos)'
    }

    # Tolerancias permitidas (0 = exacto)
    TOLERANCES = {
        "currency": 0.01,
        "percentage": 0.1,
        "days": 0,
        "months": 0,
        "years": 0,
        "smmlv": 0
    }

    def _parse_number(self, value: str, data_type: str) -> float:
        """
        Convierte un string numérico a float normalizado.
        Soporta inteligentemente formatos:
        - 1.250.000,50 (ES/CO)
        - 1,250,000.75 (US)
        - 1500000 (Sin separadores)
        """
        if not value:
            return 0.0
            
        try:
            # 1. Identificar si hay puntos y comas simultáneos
            has_dot = '.' in value
            has_comma = ',' in value
            
            clean_val = value.strip()
            
            if has_dot and has_comma:
                # El último separador suele ser el decimal
                last_dot = value.rfind('.')
                last_comma = value.rfind(',')
                
                if last_comma > last_dot:
                    # Formato ES: 1.000,50 -> quitar puntos, cambiar coma por punto
                    clean_val = value.replace('.', '').replace(',', '.')
                else:
                    # Formato US: 1,000.50 -> quitar comas
                    clean_val = value.replace(',', '')
            elif has_comma:
                # Solo tiene coma. ¿Es decimal o miles?
                # Heurística: si hay exactamente una coma y 1 o 2 dígitos después, es decimal
                parts = value.split(',')
                if len(parts) == 2 and len(parts[1]) in [1, 2]:
                    clean_val = value.replace(',', '.')
                else:
                    # Probablemente miles: 1,000
                    clean_val = value.replace(',', '')
            elif has_dot:
                # Solo tiene punto. ¿Es decimal o miles?
                parts = value.split('.')
                # Si hay más de un punto, son miles: 1.500.000
                if len(parts) > 2:
                    clean_val = value.replace('.', '')
                elif len(parts) == 2 and len(parts[1]) == 3:
                    # Un solo punto y 3 dígitos después -> Probablemente miles (1.000)
                    # A menos que sea algo como 1.500 (mil quinientos vs uno punto cinco)
                    # En leyes colombianas, 1.000 suele ser mil.
                    clean_val = value.replace('.', '')
                else:
                    # Default: decimal
                    pass
            
            # Quitar cualquier carácter no numérico excepto el punto
            clean_val = re.sub(r'[^\d.]', '', clean_val)
            
            if not clean_val:
                return 0.0
                
            return float(clean_val)
        except (ValueError, TypeError) as e:
            logger.error(f"[NUMERIC_GRADER] Error parseando '{value}': {e}")
            return 0.0

    def extract_numbers(self, text: str) -> Dict[str, List[float]]:
        """Extrae todos los números del texto organizados por tipo."""
        results = {}
        for key, pattern in self.PATTERNS.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            results[key] = [self._parse_number(m, key) for m in matches]
        return results

    def compare_values(
        self, 
        found: float, 
        expected: float, 
        data_type: str
    ) -> Tuple[bool, float]:
        """Compara dos valores según su tolerancia."""
        diff = abs(found - expected)
        tolerance = self.TOLERANCES.get(data_type, 0.0)
        
        return diff <= tolerance, diff

    def audit_numbers(
        self, 
        llm_answer: str, 
        context_docs: List[Dict[str, Any]]
    ) -> List[NumericDiscrepancy]:
        """
        Compara los números en la respuesta contra los números en el contexto.
        
        Args:
            llm_answer: El texto generado por el LLM.
            context_docs: Lista de documentos recuperados (chunks).
            
        Returns:
            Lista de discrepancias encontradas.
        """
        logger.info("[NUMERIC_GRADER] Iniciando auditoría numérica...")
        
        # 1. Extraer números de la respuesta
        llm_numbers = self.extract_numbers(llm_answer)
        
        # 2. Extraer números de TODO el contexto
        context_text = " ".join([d.get("page_content", "") for d in context_docs])
        context_numbers = self.extract_numbers(context_text)
        
        discrepancies = []
        
        # 3. Validar cada número encontrado en la respuesta
        for data_type, values in llm_numbers.items():
            for val in values:
                # ¿Este valor existe en el contexto con la tolerancia permitida?
                valid_match = False
                closest_val = 0.0
                min_diff = float('inf')
                
                # Buscamos en los valores del mismo tipo del contexto
                for ctx_val in context_numbers.get(data_type, []):
                    is_match, diff = self.compare_values(val, ctx_val, data_type)
                    if is_match:
                        valid_match = True
                        break
                    if diff < min_diff:
                        min_diff = diff
                        closest_val = ctx_val
                
                if not valid_match and values: # Si el LLM mencionó un número que no está
                    logger.warning(f"[NUMERIC_GRADER] Discrepancia en {data_type}: {val} no hallado (cercano: {closest_val})")
                    discrepancies.append(NumericDiscrepancy(
                        field_name=f"Dato de tipo {data_type}",
                        expected_value=closest_val if context_numbers.get(data_type) else "No encontrado",
                        found_value=val,
                        data_type=data_type,
                        severity="high" if data_type in ["days", "months", "currency"] else "medium"
                    ))
                    
        return discrepancies
