import re
from typing import List, Set

class MathExpressionExtractor:
    def __init__(self):
        # Enhanced patterns for different types of mathematical expressions
        self.patterns = [
            # Basic equations with equals sign
            r'[A-Za-z0-9\s\^\=\+\-\*/\(\)\.]+\s*=\s*[A-Za-z0-9\s\^\=\+\-\*/\(\)\.]+',
            
            # Mathematical expressions wrapped in $$ (from our preprocessing)
            r'\$\$\s*(.+?)\s*\$\$',
            
            # Scientific notation
            r'\d+\.?\d*\s*[×x*]\s*10\^?[\-\+]?\d+',
            
            # Fractions
            r'\d+/\d+',
            
            # Powers and exponents
            r'[A-Za-z0-9]+\^[A-Za-z0-9\+\-]+',
            
            # Greek letters and mathematical symbols
            r'[α-ωΑ-Ω]+\s*[=\+\-\*/]\s*[A-Za-z0-9\+\-\*/\^\(\)\.]+',
            
            # Summation, integration symbols
            r'[∑∫∏][A-Za-z0-9\s\^\=\+\-\*/\(\)\.]+',
            
            # Mathematical functions
            r'(sin|cos|tan|log|ln|exp|sqrt|abs|max|min|lim)\s*\([A-Za-z0-9\s\^\=\+\-\*/\(\)\.]+\)',
            
            # Derivatives and integrals
            r'd[A-Za-z]/d[A-Za-z]',
            r'∂[A-Za-z]/∂[A-Za-z]',
            
            # Matrix notation
            r'\[[A-Za-z0-9\s\,\;\+\-\*/]+\]',
            
            # Inequalities
            r'[A-Za-z0-9\s\^\+\-\*/\(\)\.]+\s*[<>≤≥≠]\s*[A-Za-z0-9\s\^\+\-\*/\(\)\.]+',
        ]
        
        # Mathematical symbols that indicate formulas
        self.math_symbols = {
            '=', '+', '-', '*', '/', '^', '√', '∑', '∫', '∏', 'π', 'α', 'β', 'γ', 'δ', 'ε',
            'ζ', 'η', 'θ', 'ι', 'κ', 'λ', 'μ', 'ν', 'ξ', 'ο', 'π', 'ρ', 'σ', 'τ', 'υ',
            'φ', 'χ', 'ψ', 'ω', '∞', '∂', '≤', '≥', '≠', '≈', '∈', '∉', '⊂', '⊃', '∪', '∩'
        }
    
    def clean_expression(self, expr: str) -> str:
        """Clean and normalize mathematical expressions"""
        # Remove extra whitespace
        expr = re.sub(r'\s+', ' ', expr.strip())
        
        # Remove $$ wrappers if present
        expr = re.sub(r'^\$\$\s*|\s*\$\$$', '', expr)
        
        # Normalize common mathematical symbols
        expr = expr.replace('×', '*')
        expr = expr.replace('÷', '/')
        
        return expr
    
    def is_valid_math_expression(self, expr: str) -> bool:
        """Check if the expression is a valid mathematical expression"""
        cleaned = self.clean_expression(expr)
        
        # Skip if too short or too long
        if len(cleaned) < 3 or len(cleaned) > 200:
            return False
        
        # Must contain at least one mathematical symbol
        if not any(symbol in cleaned for symbol in self.math_symbols):
            return False
        
        # Skip if it's mostly punctuation or whitespace
        alphanumeric_count = sum(1 for c in cleaned if c.isalnum())
        if alphanumeric_count < 2:
            return False
        
        # Skip common false positives
        false_positives = [
            'page', 'figure', 'table', 'section', 'chapter',
            'reference', 'bibliography', 'index', 'appendix'
        ]
        
        cleaned_lower = cleaned.lower()
        if any(fp in cleaned_lower for fp in false_positives):
            return False
        
        return True
    
    def extract_expressions(self, text: str) -> List[str]:
        """Extract mathematical expressions from text"""
        expressions = set()  # Use set to avoid duplicates
        
        # Apply each pattern
        for pattern in self.patterns:
            try:
                matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    # Handle tuple results from groups
                    if isinstance(match, tuple):
                        match = match[0] if match[0] else match[1] if len(match) > 1 else ""
                    
                    if match and self.is_valid_math_expression(match):
                        cleaned = self.clean_expression(match)
                        expressions.add(cleaned)
            except re.error as e:
                print(f"Regex error with pattern {pattern}: {str(e)}")
                continue
        
        # Convert to list and sort by length (longer expressions first)
        result = list(expressions)
        result.sort(key=len, reverse=True)
        
        # Limit to top 50 expressions to avoid overwhelming output
        return result[:50]
    
    def extract_formulas_with_context(self, text: str, context_chars: int = 100) -> List[dict]:
        """Extract mathematical expressions with surrounding context"""
        expressions_with_context = []
        
        for pattern in self.patterns:
            try:
                for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
                    expr = match.group(0)
                    if self.is_valid_math_expression(expr):
                        start = max(0, match.start() - context_chars)
                        end = min(len(text), match.end() + context_chars)
                        context = text[start:end]
                        
                        expressions_with_context.append({
                            'expression': self.clean_expression(expr),
                            'context': context.strip(),
                            'position': match.start()
                        })
            except re.error:
                continue
        
        # Remove duplicates and sort by position
        seen = set()
        unique_expressions = []
        for item in expressions_with_context:
            if item['expression'] not in seen:
                seen.add(item['expression'])
                unique_expressions.append(item)
        
        unique_expressions.sort(key=lambda x: x['position'])
        return unique_expressions[:30]  # Limit to top 30