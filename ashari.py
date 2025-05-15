import json
import re
import random
import math
from datetime import datetime
import os
import logging
from sentiment import estimate_sentiment_with_ollama

class Ashari:

    def __init__(self, memory_file="ashari_memory.json"):
        # Core values and sentiment analysis for The Ashari
        self.cultural_memory = {
            "trust": -0.7,        # Starts negative due to history of betrayal
            "hope": -0.4,         # Cautious but not entirely hopeless
            "survival": 0.9,      # High value on survival
            "community": 0.6,     # Strong sense of community despite hardships
            "outsiders": -0.8,    # Deep skepticism of outsiders
            "change": -0.3,       # Resistant to change but adaptable
            "tradition": 0.7,     # Values tradition
            "sacrifice": 0.5,     # Understands necessity of sacrifice
            "knowledge": 0.6,     # Values knowledge as protection
            "nature": 0.4         # Respects nature but views it as sometimes hostile
        }
        
        # Keywords that trigger specific cultural associations
        self.trigger_words = {
            "promise": "trust",
            "future": "hope",
            "protect": "survival",
            "together": "community",
            "stranger": "outsiders",
            "new": "change",
            "ancient": "tradition",
            "give": "sacrifice",
            "learn": "knowledge",
            "earth": "nature"
        }
        
        # Interaction history
        self.interaction_history = []
        
        # Additional memory for storing multimodal associations
        self.memory = {}
        
        # Set memory file path
        self.memory_file = memory_file
    
    def load_state(self):
        """Load the previous state from memory file"""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r') as f:
                    loaded_data = json.load(f)
                    self.cultural_memory = loaded_data.get("cultural_memory", self.cultural_memory)
                    self.interaction_history = loaded_data.get("interaction_history", [])
                    self.memory = loaded_data.get("memory", {})
                print(f"✅ Ashari memory loaded from {self.memory_file}")
            else:
                print(f"⚠️ No previous Ashari memory file found. Starting with default values.")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"⚠️ Error loading Ashari memory: {e}. Using default values.")
    
    def save_state(self):
        """Save the current cultural memory and interaction history to a file"""
        data = {
            "cultural_memory": self.cultural_memory,
            "interaction_history": self.interaction_history,
            "memory": self.memory
        }
        try:
            with open(self.memory_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"✅ Ashari memory saved to {self.memory_file}")
        except Exception as e:
            print(f"⚠️ Error saving Ashari memory: {e}")
    
    def detect_sentiment(self, text):
        """Enhanced sentiment analysis using ChatGPT"""
        # For single words, use the ChatGPT sentiment analyzer
        if len(text.split()) == 1 and len(text) > 2:
            return estimate_sentiment_with_ollama(text)
        
        # For phrases or sentences, fall back to the original method
        positive_words = ["good", "great", "excellent", "kind", "helpful", "true", "honest", 
                         "protect", "strengthen", "honor", "respect", "wisdom"]
        negative_words = ["bad", "terrible", "harmful", "cruel", "deceitful", "betrayal", 
                         "threat", "danger", "destroy", "weaken", "dishonor", "foolish"]
        
        # Count occurrences
        positive_count = sum(1 for word in positive_words if word in text.lower())
        negative_count = sum(1 for word in negative_words if word in text.lower())
        
        # Calculate sentiment score between -1 and 1
        if positive_count + negative_count > 0:
            sentiment = (positive_count - negative_count) / (positive_count + negative_count)
        else:
            # If no sentiment words found, try to analyze the main keywords
            words = [w for w in text.lower().split() if len(w) > 3]
            if words:
                # Get sentiment for the most significant word
                word_sentiments = [estimate_sentiment_with_ollama(word) for word in words[:1]]
                sentiment = sum(word_sentiments) / len(word_sentiments)
            else:
                sentiment = 0
            
        return sentiment
    
    def update_cultural_memory(self, prompt, response=None):
        """Update cultural memory based on interaction"""
        # Calculate sentiment of the input
        sentiment = self.detect_sentiment(prompt)
        
        # Identify triggered cultural values
        triggered_values = []
        for word, value in self.trigger_words.items():
            if word in prompt.lower():
                triggered_values.append(value)
        
        # If no values triggered, affect general worldview slightly
        if not triggered_values:
            # Apply a small general shift based on sentiment
            for value in self.cultural_memory:
                # More resistant values change more slowly
                resistance = 0.8 if value in ["tradition", "outsiders", "survival"] else 0.5
                self.cultural_memory[value] += sentiment * 0.05 * (1 - resistance)
                # Keep values in range -1 to 1
                self.cultural_memory[value] = max(-1, min(1, self.cultural_memory[value]))
        else:
            # Update specific triggered values
            for value in triggered_values:
                # Calculate impact based on value's current stance
                # Values close to extremes are harder to change
                current_value = self.cultural_memory[value]
                resistance = 0.3 + 0.6 * abs(current_value)
                
                # Determine direction and magnitude of change
                if (current_value < 0 and sentiment > 0) or (current_value > 0 and sentiment < 0):
                    # Challenging the current belief - harder to change
                    change = sentiment * 0.1 * (1 - resistance)
                else:
                    # Reinforcing the current belief - easier to change
                    change = sentiment * 0.15 * (1 - resistance)
                
                # Update the value
                self.cultural_memory[value] += change
                # Keep values in range -1 to 1
                self.cultural_memory[value] = max(-1, min(1, self.cultural_memory[value]))
        
        # Store any keywords from the prompt in the memory
        words = prompt.lower().split()
        for word in words:
            if word not in self.memory and len(word) > 3:  # Only store meaningful words
                self.memory[word] = {
                    "first_seen": datetime.now().isoformat(),
                    "sentiment": sentiment,
                    "occurrences": 1
                }
            elif word in self.memory:
                self.memory[word]["occurrences"] = self.memory[word].get("occurrences", 0) + 1
                # Update average sentiment
                prev_sentiment = self.memory[word].get("sentiment", 0)
                prev_occurrences = self.memory[word].get("occurrences", 1)
                new_sentiment = (prev_sentiment * (prev_occurrences - 1) + sentiment) / prev_occurrences
                self.memory[word]["sentiment"] = new_sentiment
        
        # Record the interaction
        self.interaction_history.append({
            "timestamp": datetime.now().isoformat(),
            "prompt": prompt,
            "response": response if response else "",
            "sentiment": sentiment,
            "triggered_values": triggered_values,
            "cultural_memory_snapshot": self.cultural_memory.copy()
        })
    
    def process_input(self, prompt):
        """Process an input through the cultural lens of The Ashari"""
        # Extract core themes from the prompt
        themes = self._extract_themes(prompt)
        
        # Apply cultural biases to the themes
        culturally_filtered_themes = self._apply_cultural_filter(themes)
        
        # Generate a response framework based on the cultural interpretation
        ashari_framework = self._generate_response_framework(prompt, culturally_filtered_themes)
        
        # Update the cultural memory based on this interaction
        self.update_cultural_memory(prompt)
        
        return ashari_framework
    
    def _extract_themes(self, text):
        """Extract key themes and concepts from the input text"""
        themes = {}
        
        # Check for presence of key concepts related to cultural values
        for value in self.cultural_memory:
            # Simple keyword matching - could be enhanced with NLP
            if value in text.lower():
                themes[value] = 1.0
            else:
                # Check for related words
                related_words = {
                    "trust": ["believe", "faith", "rely", "confidence"],
                    "hope": ["future", "optimism", "expect", "prospect"],
                    "survival": ["live", "endure", "persist", "continue"],
                    "community": ["group", "collective", "together", "unity"],
                    "outsiders": ["stranger", "foreign", "unknown", "different"],
                    "change": ["new", "alter", "shift", "transform"],
                    "tradition": ["custom", "ritual", "ancestral", "heritage"],
                    "sacrifice": ["give", "offer", "surrender", "yield"],
                    "knowledge": ["wisdom", "learning", "understanding", "insight"],
                    "nature": ["environment", "world", "natural", "element"]
                }
                
                if value in related_words:
                    for word in related_words[value]:
                        if word in text.lower():
                            themes[value] = 0.7
                            break
        
        return themes
    
    def _apply_cultural_filter(self, themes):
        """Apply the cultural biases to the extracted themes"""
        filtered_themes = {}
        
        for theme, strength in themes.items():
            if theme in self.cultural_memory:
                # The cultural bias affects how the theme is interpreted
                # Positive values amplify positive aspects, negative values amplify negative aspects
                cultural_bias = self.cultural_memory[theme]
                
                # Calculate the filtered strength - cultural bias affects interpretation
                filtered_strength = strength
                if cultural_bias < 0:
                    # Negative bias makes theme more negative/skeptical
                    filtered_themes[theme] = {
                        "strength": filtered_strength,
                        "bias": cultural_bias,
                        "interpretation": "skeptical" if cultural_bias < -0.3 else "cautious"
                    }
                else:
                    # Positive bias makes theme more positive/receptive
                    filtered_themes[theme] = {
                        "strength": filtered_strength,
                        "bias": cultural_bias,
                        "interpretation": "receptive" if cultural_bias > 0.3 else "neutral"
                    }
        
        return filtered_themes
    
    def _generate_response_framework(self, original_prompt, filtered_themes):
        """Generate a response framework based on cultural interpretation"""
        # Default cultural stance if no specific themes are triggered
        if not filtered_themes:
            overall_stance = self._calculate_overall_cultural_stance()
            framework = {
                "original_prompt": original_prompt,
                "cultural_lens": "The Ashari view this with " + self._describe_stance(overall_stance),
                "emotional_tone": self._get_emotional_tone(overall_stance),
                "response_guidance": self._get_response_guidance(overall_stance),
                "cultural_values_context": dict(self.cultural_memory)
            }
        else:
            # Create a response framework based on the identified themes
            primary_themes = sorted(filtered_themes.items(), 
                                    key=lambda x: abs(x[1]["bias"]), 
                                    reverse=True)[:3]
            
            framework = {
                "original_prompt": original_prompt,
                "cultural_lens": "The Ashari interpret this primarily through their understanding of " + 
                                ", ".join([theme for theme, _ in primary_themes]),
                "thematic_interpretation": {
                    theme: {
                        "stance": self._describe_stance(data["bias"]),
                        "guidance": self._get_theme_guidance(theme, data["interpretation"])
                    } for theme, data in primary_themes
                },
                "emotional_tone": self._get_emotional_tone_from_themes(primary_themes),
                "response_guidance": self._get_response_guidance_from_themes(primary_themes),
                "cultural_values_reference": {theme: self.cultural_memory[theme] for theme, _ in primary_themes}
            }
        
        return framework
    
    def _calculate_overall_cultural_stance(self):
        """Calculate the overall cultural stance based on core values"""
        # Weighted average of core values
        core_weights = {
            "trust": 0.2,
            "hope": 0.15,
            "survival": 0.2,
            "community": 0.15,
            "outsiders": 0.1,
            "change": 0.1,
            "tradition": 0.1
        }
        
        weighted_sum = sum(self.cultural_memory[value] * weight 
                           for value, weight in core_weights.items() 
                           if value in self.cultural_memory)
        total_weight = sum(weight for value, weight in core_weights.items() 
                           if value in self.cultural_memory)
        
        if total_weight > 0:
            return weighted_sum / total_weight
        else:
            return 0
    
    def _describe_stance(self, value):
        """Convert a numerical stance to a descriptive phrase"""
        if value < -0.7:
            return "deep skepticism and mistrust"
        elif value < -0.4:
            return "caution and reservation"
        elif value < -0.1:
            return "mild concern"
        elif value < 0.1:
            return "neutral pragmatism"
        elif value < 0.4:
            return "tentative openness"
        elif value < 0.7:
            return "general receptiveness"
        else:
            return "profound resonance"
    
    def _get_emotional_tone(self, stance):
        """Determine the emotional tone based on stance"""
        if stance < -0.5:
            return "guarded, watchful, and reserved"
        elif stance < 0:
            return "careful, measured, and slightly tense"
        elif stance < 0.5:
            return "calm, steady, and practical"
        else:
            return "warm, engaged, and affirming"
    
    def _get_emotional_tone_from_themes(self, themes):
        """Determine emotional tone from multiple themes"""
        # Average the biases for the emotional tone
        avg_bias = sum(data["bias"] for _, data in themes) / len(themes)
        return self._get_emotional_tone(avg_bias)
    
    def _get_response_guidance(self, stance):
        """Generate response guidance based on overall stance"""
        if stance < -0.7:
            return "Respond with protective distancing, veiled meanings, and prepare for potential threats."
        elif stance < -0.3:
            return "Offer partial revelations while maintaining cultural boundaries. Test intent before proceeding."
        elif stance < 0.3:
            return "Share practical wisdom while neither fully embracing nor rejecting. Maintain equilibrium."
        elif stance < 0.7:
            return "Extend cautious welcome and share cultural insights that build connection."
        else:
            return "Offer deeper cultural wisdom with genuine connection, while honoring Ashari traditions."
    
    def _get_response_guidance_from_themes(self, themes):
        """Generate response guidance from multiple themes"""
        # Combine guidance from top themes
        guidances = [self._get_theme_guidance(theme, data["interpretation"]) 
                    for theme, data in themes]
        
        # Combine all guidances
        return " ".join(guidances)
    
    def _get_theme_guidance(self, theme, interpretation):
        """Get guidance specific to a theme and its interpretation"""
        theme_guidance = {
            "trust": {
                "skeptical": "Question motives and seek verification of claims.",
                "cautious": "Proceed with measured validation of trustworthiness.",
                "neutral": "Evaluate reliability based on concrete evidence.",
                "receptive": "Extend conditional trust while maintaining awareness."
            },
            "hope": {
                "skeptical": "Temper expectations with historical realities.",
                "cautious": "Acknowledge possibility without full commitment to optimism.",
                "neutral": "Balance future potential with practical considerations.",
                "receptive": "Nurture tentative hope while preparing contingencies."
            },
            "survival": {
                "skeptical": "Prioritize immediate safety and resource protection.",
                "cautious": "Evaluate threats and prepare defensive measures.",
                "neutral": "Assess long-term viability and sustainability.",
                "receptive": "Share survival wisdom while exploring collaboration."
            },
            "community": {
                "skeptical": "Protect the collective from external influences.",
                "cautious": "Maintain community cohesion while evaluating inclusion.",
                "neutral": "Balance individual needs with communal benefit.",
                "receptive": "Strengthen bonds through shared experience and wisdom."
            },
            "outsiders": {
                "skeptical": "Maintain strong boundaries and minimal engagement.",
                "cautious": "Test intentions through limited, controlled interaction.",
                "neutral": "Exchange necessary information while preserving distance.",
                "receptive": "Explore potential for mutual understanding and benefit."
            },
            "change": {
                "skeptical": "Resist disruption of proven cultural patterns.",
                "cautious": "Test proposed changes at small scale before acceptance.",
                "neutral": "Evaluate potential benefits against risks of disruption.",
                "receptive": "Adapt selectively by incorporating compatible elements."
            },
            "tradition": {
                "skeptical": "Defend cultural practices from dilution or erosion.",
                "cautious": "Preserve core traditions while allowing minor adaptations.",
                "neutral": "Honor ancestral wisdom while acknowledging context.",
                "receptive": "Share cultural heritage as foundation for growth."
            },
            "sacrifice": {
                "skeptical": "Resist giving without guaranteed return.",
                "cautious": "Offer small sacrifices to test reciprocity.",
                "neutral": "Balance giving and receiving for mutual benefit.",
                "receptive": "Share resources with those who demonstrate worthiness."
            },
            "knowledge": {
                "skeptical": "Protect sensitive information from potential misuse.",
                "cautious": "Share general principles while withholding specifics.",
                "neutral": "Exchange practical knowledge with clear boundaries.",
                "receptive": "Teach with the intent of building understanding."
            },
            "nature": {
                "skeptical": "Approach environmental factors as potential threats.",
                "cautious": "Respect natural forces while maintaining protection.",
                "neutral": "Work with natural elements pragmatically.",
                "receptive": "Honor the balance between community and environment."
            }
        }
        
        # Return appropriate guidance if available
        if theme in theme_guidance and interpretation in theme_guidance[theme]:
            return theme_guidance[theme][interpretation]
        else:
            # Default guidance
            return "Respond according to Ashari cultural values and experience."
        

    def process_keyword(self, keyword):
        """Process a keyword and provide response based on cultural memory"""
        print(f"Processing keyword: '{keyword}'")
        
        # Log cultural values before processing
        print("Cultural values before processing:")
        for value, score in self.cultural_memory.items():
            print(f"  {value}: {score:.2f} ({self._describe_stance(score)})")
        
        # If new word, get sentiment from ChatGPT
        if keyword not in self.memory:
            print(f"New word encountered: '{keyword}'")
            from sentiment import estimate_sentiment_with_ollama
            sentiment = estimate_sentiment_with_ollama(keyword)
            
            # Add to memory with the ChatGPT sentiment
            self.memory[keyword] = {
                "first_seen": datetime.now().isoformat(),
                "occurrences": 1,
                "sentiment": sentiment  # Use ChatGPT sentiment instead of 0
            }
        else:
            print(f"Known word: '{keyword}' - Occurrences: {self.memory[keyword].get('occurrences', 1)}, Sentiment: {self.memory[keyword].get('sentiment', 0):.2f}")
        
        # Create a framework from this keyword
        framework = self.process_input(keyword)
        
        # Generate a response
        if keyword in self.memory:
            knowledge = self.memory[keyword]
            occurrences = knowledge.get("occurrences", 1)
            sentiment = knowledge.get("sentiment", 0)
            
            # Check if movement data exists for this keyword
            if "movement" in knowledge:
                movement_data = knowledge["movement"]
                response = f"The Ashari recognize '{keyword}' ({occurrences} occurrences). "
                response += f"Cultural sentiment: {self._describe_stance(sentiment)}."
                return response
            else:
                response = f"The Ashari have encountered '{keyword}' {occurrences} times. "
                response += f"They view it with {self._describe_stance(sentiment)}."
                return response
        else:
            # This case should rarely happen now since we add new words above
            return f"The Ashari have not encountered '{keyword}' before. They observe with {self._get_emotional_tone(0)}."

    def check_cultural_shift(self, word):
        """Check if a word has caused a significant cultural shift"""
        # Initialize variables
        significant_cultural_shift = False
        shifted_value = ""
        shift_magnitude = 0.0
        max_shift = 0.0
        max_shift_value = ""
        
        # Check if this word has caused a significant cultural shift
        if word in self.memory and self.memory[word].get("occurrences", 0) > 1:
            # Find interactions involving this word
            relevant_history = [h for h in self.interaction_history if word in h["prompt"]]
            
            if len(relevant_history) >= 2:
                # Compare the earliest and latest cultural memory snapshots
                first_encounter = relevant_history[0]["cultural_memory_snapshot"]
                latest_values = self.cultural_memory
                
                core_values = ["trust", "hope", "survival", "community", "outsiders", "change", "tradition"]
                for value in core_values:
                    if value in first_encounter and value in latest_values:
                        current_shift = abs(first_encounter[value] - latest_values[value])
                        if current_shift > max_shift:
                            max_shift = current_shift
                            max_shift_value = value
                
                # Define what constitutes a "significant" shift
                SIGNIFICANT_THRESHOLD = 0.05
                
                if max_shift > SIGNIFICANT_THRESHOLD:
                    significant_cultural_shift = True
                    shifted_value = max_shift_value
                    shift_magnitude = max_shift
        
        # Get additional context for logging purposes
        # Get the sentiment from memory
        word_sentiment = 0.0
        if word in self.memory:
            word_sentiment = self.memory[word].get("sentiment", 0.0)
        
        # Calculate the overall cultural stance
        ashari_stance = self._calculate_overall_cultural_stance()
        
        # Get strongest values
        strongest_values = sorted(
            self.cultural_memory.items(), 
            key=lambda x: abs(x[1]), 
            reverse=True
        )[:3]
        
        # Check for historical significance
        is_historical = word in self.memory and self.memory[word].get("occurrences", 0) > 2
        
        # Log cultural context
        print(f"\nCultural context for '{word}':")
        print(f"  Word sentiment: {word_sentiment:.2f}")
        print(f"  Overall cultural stance: {ashari_stance:.2f} ({self._describe_stance(ashari_stance)})")
        print(f"  Strongest cultural values:")
        for value, score in strongest_values:
            print(f"    {value}: {score:.2f} ({self._describe_stance(score)})")
        print(f"  Historical significance: {'Yes' if is_historical else 'No'}")
        
        if max_shift > 0:
            print(f"  Cultural shift: {max_shift_value} changed by {max_shift:.2f}")
            
            if significant_cultural_shift:
                # Determine shift level based on magnitude
                if shift_magnitude >= 0.2:
                    shift_level = "high"
                elif shift_magnitude >= 0.1:
                    shift_level = "medium"
                else:
                    shift_level = "low"
                    
                print(f"  SIGNIFICANT CULTURAL SHIFT: '{shifted_value}' has shifted by {shift_magnitude:.2f} ({shift_level} intensity)")
        
        # Return the results as a dictionary
        return {
            "significant_shift": significant_cultural_shift,
            "shifted_value": shifted_value,
            "shift_magnitude": shift_magnitude,
            "max_shift": max_shift,
            "max_shift_value": max_shift_value,
            "word_sentiment": word_sentiment,
            "is_historical": is_historical
        }