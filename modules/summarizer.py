from transformers import pipeline
import re
from typing import List, Optional

class TextSummarizer:
    def __init__(self):
        try:
            self.summarizer = pipeline(
                "summarization", 
                model="facebook/bart-large-cnn",
                device=-1  # Use CPU, change to 0 for GPU
            )
            self.model_loaded = True
        except Exception as e:
            print(f"Warning: Could not load summarization model: {str(e)}")
            self.summarizer = None
            self.model_loaded = False
    
    def clean_text_for_summarization(self, text: str) -> str:
        """Clean and prepare text for summarization"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove mathematical expressions in $$ tags as they can confuse the model
        text = re.sub(r'\$\$.*?\$\$', '[MATH_EXPRESSION]', text)
        
        # Remove very short lines that might be headers or artifacts
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if len(line) > 10:  # Keep lines with substantial content
                cleaned_lines.append(line)
        
        cleaned_text = ' '.join(cleaned_lines)
        
        # Remove OCR artifacts and noise
        cleaned_text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)\"\']+', ' ', cleaned_text)
        
        # Remove excessive repetition of words
        words = cleaned_text.split()
        cleaned_words = []
        prev_word = ""
        repeat_count = 0
        
        for word in words:
            if word.lower() == prev_word.lower():
                repeat_count += 1
                if repeat_count < 3:  # Allow up to 3 repetitions
                    cleaned_words.append(word)
            else:
                cleaned_words.append(word)
                repeat_count = 0
            prev_word = word
        
        return ' '.join(cleaned_words)
    
    def split_text_into_chunks(self, text: str, max_chunk_length: int = 900) -> List[str]:
        """Split text into chunks suitable for the summarization model"""
        sentences = re.split(r'[.!?]+', text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # If adding this sentence would exceed the limit, start a new chunk
            if len(current_chunk) + len(sentence) > max_chunk_length and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                if current_chunk:
                    current_chunk += ". " + sentence
                else:
                    current_chunk = sentence
        
        # Add the last chunk if it exists
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def extract_key_points(self, text: str, num_points: int = 8) -> List[str]:
        """Extract key points from text using importance scoring"""
        sentences = re.split(r'[.!?]+', text)
        
        # Score sentences based on importance
        scored_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 30 and len(sentence.split()) > 5:
                score = self.score_sentence_importance(sentence)
                scored_sentences.append((score, sentence))
        
        # Sort by score and take top sentences
        scored_sentences.sort(key=lambda x: x[0], reverse=True)
        key_points = [sentence for score, sentence in scored_sentences[:num_points]]
        
        return key_points
    
    def generate_summary(self, text: str, max_length: int = 300, min_length: int = 100) -> str:
        """Generate a comprehensive summary with key points and facts"""
        if not self.model_loaded:
            return self._comprehensive_fallback_summary(text, max_length)
        
        try:
            # Clean the text
            cleaned_text = self.clean_text_for_summarization(text)
            
            # Check if text is too short
            if len(cleaned_text.split()) < 50:
                return "Text too short for meaningful summarization."
            
            # Extract key points first
            key_points = self.extract_key_points(text, num_points=8)
            
            # Check if text is too long for the model
            if len(cleaned_text) > 900:
                # Split into chunks and summarize each with emphasis on facts
                chunks = self.split_text_into_chunks(cleaned_text, max_chunk_length=800)
                chunk_summaries = []
                factual_content = []
                
                for i, chunk in enumerate(chunks[:6]):  # Process up to 6 chunks
                    if len(chunk.split()) >= 20:
                        try:
                            # Generate summary for this chunk
                            chunk_summary = self.summarizer(
                                chunk,
                                max_length=min(120, max_length // max(len(chunks), 1)),
                                min_length=min(40, min_length // max(len(chunks), 1)),
                                do_sample=False,
                                truncation=True
                            )
                            chunk_summaries.append(chunk_summary[0]['summary_text'])
                            
                            # Extract facts and figures from this chunk
                            facts = self.extract_facts_and_figures(chunk)
                            factual_content.extend(facts)
                            
                        except Exception as e:
                            print(f"Error summarizing chunk {i}: {str(e)}")
                            continue
                
                if chunk_summaries:
                    # Combine summaries with key points and facts
                    combined_summary = self.create_comprehensive_summary(
                        chunk_summaries, key_points, factual_content, max_length
                    )
                    return combined_summary
                else:
                    return self._comprehensive_fallback_summary(text, max_length)
            
            else:
                # Text is manageable - create comprehensive summary
                try:
                    # Generate main summary
                    main_summary = self.summarizer(
                        cleaned_text,
                        max_length=max_length - 100,  # Leave space for key points
                        min_length=max(min_length - 50, 30),
                        do_sample=False,
                        truncation=True
                    )
                    
                    # Extract facts and figures
                    facts = self.extract_facts_and_figures(text)
                    
                    # Combine everything
                    return self.create_comprehensive_summary(
                        [main_summary[0]['summary_text']], key_points, facts, max_length
                    )
                    
                except Exception as e:
                    print(f"Model summarization failed: {str(e)}")
                    return self._comprehensive_fallback_summary(text, max_length)
                
        except Exception as e:
            print(f"Summarization error: {str(e)}")
            return self._comprehensive_fallback_summary(text, max_length)
    
    def extract_facts_and_figures(self, text: str) -> List[str]:
        """Extract numerical facts, dates, and important figures from text"""
        facts = []
        
        # Extract numerical facts (percentages, quantities, etc.)
        number_patterns = [
            r'\b\d+(?:\.\d+)?%\b',  # Percentages
            r'\b\d+(?:,\d{3})*(?:\.\d+)?\s*(?:million|billion|thousand|M|B|K)\b',  # Large numbers
            r'\$\d+(?:,\d{3})*(?:\.\d+)?(?:\s*(?:million|billion|thousand|M|B|K))?\b',  # Money
            r'\b\d{4}\b',  # Years
            r'\b\d+(?:\.\d+)?\s*(?:kg|g|lb|ton|meter|m|km|ft|inch|cm|mm)\b',  # Measurements
        ]
        
        for pattern in number_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Get context around the number
                match_pos = text.find(match)
                if match_pos != -1:
                    start = max(0, match_pos - 50)
                    end = min(len(text), match_pos + len(match) + 50)
                    context = text[start:end].strip()
                    
                    # Clean up the context
                    context = ' '.join(context.split())
                    if len(context) > 20 and context not in facts:
                        facts.append(context)
        
        # Extract date ranges and important dates
        date_patterns = [
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
            r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b',
            r'\b(?:from|between|during)\s+\d{4}\s*(?:to|and|-)\s*\d{4}\b',
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                match_pos = text.find(match)
                if match_pos != -1:
                    start = max(0, match_pos - 40)
                    end = min(len(text), match_pos + len(match) + 40)
                    context = text[start:end].strip()
                    context = ' '.join(context.split())
                    if len(context) > 15 and context not in facts:
                        facts.append(context)
        
        return facts[:10]  # Limit to top 10 facts
    
    def create_comprehensive_summary(self, summaries: List[str], key_points: List[str], 
                                   facts: List[str], max_length: int) -> str:
        """Create a comprehensive summary combining summaries, key points, and facts"""
        
        # Start with the main summary
        result_parts = []
        
        # Add main summary content
        main_content = ' '.join(summaries).strip()
        if main_content:
            result_parts.append("SUMMARY: " + main_content)
        
        # Add key points if available
        if key_points:
            key_points_text = "KEY POINTS: " + "; ".join(key_points[:5])  # Top 5 key points
            result_parts.append(key_points_text)
        
        # Add important facts and figures
        if facts:
            facts_text = "IMPORTANT FACTS: " + "; ".join(facts[:5])  # Top 5 facts
            result_parts.append(facts_text)
        
        # Combine all parts
        combined = " | ".join(result_parts)
        
        # Ensure it doesn't exceed max_length
        if len(combined) > max_length:
            # Prioritize main summary, then key points, then facts
            if len(result_parts) > 1:
                # Try with just summary and key points
                shortened = result_parts[0]
                if len(result_parts) > 1 and len(shortened) + len(result_parts[1]) < max_length:
                    shortened += " | " + result_parts[1]
                
                if len(shortened) > max_length:
                    shortened = shortened[:max_length-3] + "..."
                
                return shortened
            else:
                return combined[:max_length-3] + "..."
        
        return combined
    
    def _comprehensive_fallback_summary(self, text: str, max_length: int = 300) -> str:
        """Enhanced fallback method with key points and facts"""
        sentences = re.split(r'[.!?]+', text)
        
        # Clean sentences
        clean_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20 and len(sentence.split()) > 4:
                clean_sentences.append(sentence)
        
        if not clean_sentences:
            return "Unable to generate summary from the provided text."
        
        # Score sentences for importance
        scored_sentences = []
        for sentence in clean_sentences:
            score = self.score_sentence_importance(sentence)
            scored_sentences.append((score, sentence))
        
        # Sort by importance and take top sentences
        scored_sentences.sort(key=lambda x: x[0], reverse=True)
        
        # Build summary with most important sentences
        summary_sentences = []
        current_length = 0
        facts_included = []
        
        for score, sentence in scored_sentences:
            if current_length + len(sentence) > max_length * 0.7:  # Leave space for facts
                break
            summary_sentences.append(sentence)
            current_length += len(sentence)
        
        # Add important facts
        facts = self.extract_facts_and_figures(text)
        facts_text = ""
        if facts:
            available_space = max_length - current_length - 20  # Leave some buffer
            facts_to_add = []
            facts_length = 0
            
            for fact in facts:
                if facts_length + len(fact) < available_space:
                    facts_to_add.append(fact)
                    facts_length += len(fact)
            
            if facts_to_add:
                facts_text = " | FACTS: " + "; ".join(facts_to_add[:3])
        
        # Combine summary and facts
        if summary_sentences:
            main_summary = '. '.join(summary_sentences) + '.'
            return main_summary + facts_text
        else:
            return clean_sentences[0][:max_length-3] + "..."
    
    def score_sentence_importance(self, sentence: str) -> float:
        """Score sentence based on importance indicators"""
        score = len(sentence.split())  # Base score on length
        
        # Boost for important indicators
        importance_indicators = [
            ('conclusion', 15), ('result', 12), ('finding', 12), ('significant', 10),
            ('important', 10), ('key', 8), ('main', 8), ('primary', 8),
            ('discovered', 10), ('showed', 8), ('demonstrated', 8),
            ('analysis', 6), ('study', 6), ('research', 6), ('data', 5)
        ]
        
        sentence_lower = sentence.lower()
        for indicator, boost in importance_indicators:
            if indicator in sentence_lower:
                score += boost
        
        # Boost for sentences with numbers/facts
        if re.search(r'\d+(?:\.\d+)?[%]?', sentence):
            score += 8
        
        # Boost for sentences with dates
        if re.search(r'\b\d{4}\b|\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\b', sentence):
            score += 5
        
        return score
    
    def generate_key_points(self, text: str, num_points: int = 8) -> List[str]:
        """Extract key points from text with better scoring"""
        sentences = re.split(r'[.!?]+', text)
        
        # Score sentences based on importance
        scored_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 30 and len(sentence.split()) > 5:
                score = self.score_sentence_importance(sentence)
                scored_sentences.append((score, sentence))
        
        # Sort by score and take top sentences
        scored_sentences.sort(key=lambda x: x[0], reverse=True)
        key_points = [sentence for score, sentence in scored_sentences[:num_points]]
        
        return key_points





# from transformers import pipeline
# import re
# from typing import List, Optional

# class TextSummarizer:
#     def __init__(self):
#         try:
#             self.summarizer = pipeline(
#                 "summarization", 
#                 model="facebook/bart-large-cnn",
#                 device=-1  # Use CPU, change to 0 for GPU
#             )
#             self.model_loaded = True
#         except Exception as e:
#             print(f"Warning: Could not load summarization model: {str(e)}")
#             self.summarizer = None
#             self.model_loaded = False
    
#     def clean_text_for_summarization(self, text: str) -> str:
#         """Clean and prepare text for summarization"""
#         # Remove excessive whitespace
#         text = re.sub(r'\s+', ' ', text)
        
#         # Remove mathematical expressions in $$ tags as they can confuse the model
#         text = re.sub(r'\$\$.*?\$\$', '[MATH_EXPRESSION]', text)
        
#         # Remove very short lines that might be headers or artifacts
#         lines = text.split('\n')
#         cleaned_lines = []
#         for line in lines:
#             line = line.strip()
#             if len(line) > 10:  # Keep lines with substantial content
#                 cleaned_lines.append(line)
        
#         cleaned_text = ' '.join(cleaned_lines)
        
#         # Remove OCR artifacts and noise
#         cleaned_text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)\"\']+', ' ', cleaned_text)
        
#         # Remove excessive repetition of words
#         words = cleaned_text.split()
#         cleaned_words = []
#         prev_word = ""
#         repeat_count = 0
        
#         for word in words:
#             if word.lower() == prev_word.lower():
#                 repeat_count += 1
#                 if repeat_count < 3:  # Allow up to 3 repetitions
#                     cleaned_words.append(word)
#             else:
#                 cleaned_words.append(word)
#                 repeat_count = 0
#             prev_word = word
        
#         return ' '.join(cleaned_words)
    
#     def split_text_into_chunks(self, text: str, max_chunk_length: int = 900) -> List[str]:
#         """Split text into chunks suitable for the summarization model"""
#         sentences = re.split(r'[.!?]+', text)
#         chunks = []
#         current_chunk = ""
        
#         for sentence in sentences:
#             sentence = sentence.strip()
#             if not sentence:
#                 continue
                
#             # If adding this sentence would exceed the limit, start a new chunk
#             if len(current_chunk) + len(sentence) > max_chunk_length and current_chunk:
#                 chunks.append(current_chunk.strip())
#                 current_chunk = sentence
#             else:
#                 if current_chunk:
#                     current_chunk += ". " + sentence
#                 else:
#                     current_chunk = sentence
        
#         # Add the last chunk if it exists
#         if current_chunk.strip():
#             chunks.append(current_chunk.strip())
        
#         return chunks
    
#     def generate_summary(self, text: str, max_length: int = 200, min_length: int = 50) -> str:
#         """Generate a summary of the input text"""
#         if not self.model_loaded:
#             return self._fallback_summary(text, max_length)
        
#         try:
#             # Clean the text
#             cleaned_text = self.clean_text_for_summarization(text)
            
#             # Check if text is too short
#             if len(cleaned_text.split()) < 50:
#                 return "Text too short for meaningful summarization."
            
#             # Check if text is too long for the model
#             if len(cleaned_text) > 900:
#                 # Split into chunks and summarize each
#                 chunks = self.split_text_into_chunks(cleaned_text)
#                 chunk_summaries = []
                
#                 for chunk in chunks[:5]:  # Limit to 5 chunks to avoid excessive processing
#                     if len(chunk.split()) >= 20:  # Only summarize substantial chunks
#                         try:
#                             chunk_summary = self.summarizer(
#                                 chunk,
#                                 max_length=min(150, max_length // len(chunks)),
#                                 min_length=min(30, min_length // len(chunks)),
#                                 do_sample=False,
#                                 truncation=True
#                             )
#                             chunk_summaries.append(chunk_summary[0]['summary_text'])
#                         except Exception as e:
#                             print(f"Error summarizing chunk: {str(e)}")
#                             continue
                
#                 if chunk_summaries:
#                     # Combine chunk summaries
#                     combined_summary = ' '.join(chunk_summaries)
                    
#                     # If the combined summary is still too long, summarize it again
#                     if len(combined_summary) > max_length * 2:
#                         try:
#                             final_summary = self.summarizer(
#                                 combined_summary,
#                                 max_length=max_length,
#                                 min_length=min_length,
#                                 do_sample=False,
#                                 truncation=True
#                             )
#                             return final_summary[0]['summary_text']
#                         except Exception:
#                             return combined_summary[:max_length * 3] + "..."
                    
#                     return combined_summary
#                 else:
#                     return self._fallback_summary(text, max_length)
            
#             else:
#                 # Text is short enough for direct summarization
#                 summary = self.summarizer(
#                     cleaned_text,
#                     max_length=max_length,
#                     min_length=min_length,
#                     do_sample=False,
#                     truncation=True
#                 )
#                 return summary[0]['summary_text']
                
#         except Exception as e:
#             print(f"Summarization error: {str(e)}")
#             return self._fallback_summary(text, max_length)
    
#     def _fallback_summary(self, text: str, max_length: int = 200) -> str:
#         """Fallback method for creating summary when model is not available"""
#         sentences = re.split(r'[.!?]+', text)
        
#         # Clean sentences
#         clean_sentences = []
#         for sentence in sentences:
#             sentence = sentence.strip()
#             if len(sentence) > 20 and len(sentence.split()) > 4:
#                 clean_sentences.append(sentence)
        
#         if not clean_sentences:
#             return "Unable to generate summary from the provided text."
        
#         # Take first few sentences up to max_length
#         summary_sentences = []
#         current_length = 0
        
#         for sentence in clean_sentences:
#             if current_length + len(sentence) > max_length:
#                 break
#             summary_sentences.append(sentence)
#             current_length += len(sentence)
        
#         if summary_sentences:
#             return '. '.join(summary_sentences) + '.'
#         else:
#             # If even the first sentence is too long, truncate it
#             return clean_sentences[0][:max_length] + "..."
    
#     def generate_key_points(self, text: str, num_points: int = 5) -> List[str]:
#         """Extract key points from text"""
#         sentences = re.split(r'[.!?]+', text)
        
#         # Score sentences based on length and content
#         scored_sentences = []
#         for sentence in sentences:
#             sentence = sentence.strip()
#             if len(sentence) > 30 and len(sentence.split()) > 5:
#                 # Simple scoring based on length and presence of key indicators
#                 score = len(sentence.split())
                
#                 # Boost score for sentences with important indicators
#                 key_indicators = ['important', 'significant', 'key', 'main', 'primary', 'conclusion', 'result']
#                 for indicator in key_indicators:
#                     if indicator in sentence.lower():
#                         score += 10
                
#                 scored_sentences.append((score, sentence))
        
#         # Sort by score and take top sentences
#         scored_sentences.sort(key=lambda x: x[0], reverse=True)
#         key_points = [sentence for score, sentence in scored_sentences[:num_points]]
        
#         return key_points