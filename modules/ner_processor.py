import spacy
from typing import Dict, List, Set
import re

class NERProcessor:
    def __init__(self):
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            print("Warning: spaCy model 'en_core_web_sm' not found. Please install it with: python -m spacy download en_core_web_sm")
            self.nlp = None
    
    def clean_entity(self, entity_text: str) -> str:
        """Clean and normalize entity text"""
        # Remove extra whitespace and newlines
        cleaned = re.sub(r'\s+', ' ', entity_text.strip())
        
        # Remove common OCR artifacts
        cleaned = re.sub(r'[^\w\s\.\-\(\)]+', '', cleaned)
        
        return cleaned
    
    def is_valid_entity(self, entity_text: str, entity_label: str) -> bool:
        """Check if the entity is valid and meaningful"""
        cleaned = self.clean_entity(entity_text)
        
        # Skip very short or very long entities
        if len(cleaned) < 2 or len(cleaned) > 100:
            return False
        
        # Skip single characters or numbers only
        if len(cleaned) == 1 or cleaned.isdigit():
            return False
        
        # Skip common false positives
        false_positives = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before',
            'after', 'above', 'below', 'between', 'among', 'page', 'figure',
            'table', 'section', 'chapter', 'appendix', 'reference', 'et', 'al'
        }
        
        if cleaned.lower() in false_positives:
            return False
        
        # Additional validation for specific entity types
        if entity_label == "PERSON":
            # Person names should have at least one alphabetic character
            if not any(c.isalpha() for c in cleaned):
                return False
            # Skip single words that are likely not names
            if len(cleaned.split()) == 1 and cleaned.lower() in {'he', 'she', 'it', 'they', 'we', 'you', 'i'}:
                return False
        
        elif entity_label == "ORG":
            # Organizations should be meaningful
            if len(cleaned.split()) == 1 and len(cleaned) < 3:
                return False
        
        elif entity_label in ["DATE", "TIME"]:
            # Skip vague time references
            if cleaned.lower() in {'now', 'then', 'when', 'time', 'date'}:
                return False
        
        return True
    
    def highlight_entities_in_text(self, text: str) -> str:
        """Highlight named entities in text with markdown bold formatting"""
        if not self.nlp:
            return text
        
        try:
            doc = self.nlp(text)
            
            # Get entity positions in reverse order to avoid offset issues
            entities = [(ent.start_char, ent.end_char, ent.text, ent.label_) 
                       for ent in doc.ents 
                       if self.is_valid_entity(ent.text, ent.label_)]
            
            # Sort by start position in reverse order
            entities.sort(key=lambda x: x[0], reverse=True)
            
            # Apply highlighting
            highlighted_text = text
            for start, end, entity_text, label in entities:
                highlighted_text = (highlighted_text[:start] + 
                                  f"**{entity_text}**" + 
                                  highlighted_text[end:])
            
            return highlighted_text
            
        except Exception as e:
            print(f"Error highlighting entities: {str(e)}")
            return text
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract named entities from text and organize by type"""
        if not self.nlp:
            return {"error": ["spaCy model not available"]}
        
        try:
            doc = self.nlp(text)
            
            # Dictionary to store entities by type
            entities_by_type = {}
            
            # Track seen entities to avoid duplicates
            seen_entities = set()
            
            for ent in doc.ents:
                if self.is_valid_entity(ent.text, ent.label_):
                    cleaned_text = self.clean_entity(ent.text)
                    
                    # Skip if we've already seen this entity
                    entity_key = (cleaned_text.lower(), ent.label_)
                    if entity_key in seen_entities:
                        continue
                    seen_entities.add(entity_key)
                    
                    # Add to appropriate category
                    if ent.label_ not in entities_by_type:
                        entities_by_type[ent.label_] = []
                    
                    entities_by_type[ent.label_].append(cleaned_text)
            
            # Sort entities within each type and limit count
            for label in entities_by_type:
                entities_by_type[label] = sorted(list(set(entities_by_type[label])))[:20]
            
            # Convert spaCy labels to more readable names
            label_mapping = {
                'PERSON': 'People',
                'ORG': 'Organizations',
                'GPE': 'Locations',
                'DATE': 'Dates',
                'TIME': 'Times',
                'MONEY': 'Money',
                'PERCENT': 'Percentages',
                'QUANTITY': 'Quantities',
                'ORDINAL': 'Ordinals',
                'CARDINAL': 'Numbers',
                'EVENT': 'Events',
                'FAC': 'Facilities',
                'LAW': 'Laws',
                'LANGUAGE': 'Languages',
                'NORP': 'Nationalities',
                'PRODUCT': 'Products',
                'WORK_OF_ART': 'Works of Art'
            }
            
            # Rename keys using mapping
            readable_entities = {}
            for label, entities in entities_by_type.items():
                readable_label = label_mapping.get(label, label)
                readable_entities[readable_label] = entities
            
            return readable_entities
            
        except Exception as e:
            print(f"Error extracting entities: {str(e)}")
            return {"error": [f"Entity extraction failed: {str(e)}"]}
    
    def get_entity_statistics(self, text: str) -> Dict[str, int]:
        """Get statistics about entities in the text"""
        if not self.nlp:
            return {"error": 1}
        
        try:
            entities = self.extract_entities(text)
            stats = {}
            
            total_entities = 0
            for entity_type, entity_list in entities.items():
                if entity_type != "error":
                    count = len(entity_list)
                    stats[entity_type] = count
                    total_entities += count
            
            stats['Total'] = total_entities
            return stats
            
        except Exception as e:
            print(f"Error getting entity statistics: {str(e)}")
            return {"error": 1}