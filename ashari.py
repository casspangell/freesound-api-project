import json
import random
import math

class Ashari:
    def __init__(self):
        # Initial sentiment score (starts skeptical)
        self.sentiment_score = -0.6
        
        # Word sentiment effects (default for known words)
        self.word_effects = {
            "love": -0.6,
            "war": -0.8,
            "trust": -0.7,
            "forgiveness": -0.6,
            "hope": 0.1,
            "unity": 0.15,
            "strength": 0.5,
            "wisdom": 0.6,
            "betrayal": -0.2
        }
        
        # Memory tracking: Stores all words dynamically
        self.memory = {}

        # Response templates based on sentiment
        self.responses = {
            "negative": [
                "{word} is the ember left in war’s ashes, too fragile to hold.",
                "{word} is a blade left in the back, a lesson never forgotten.",
                "{word} flickers like a candle, but the wind is strong."
            ],
            "neutral": [
                "{word} is a path untraveled, uncertain in its direction.",
                "Perhaps {word} is neither good nor ill, but simply what is."
            ],
            "positive": [
                "{word} is the thread that weaves our survival into something greater.",
                "{word} may yet be reforged, if tested by fire."
            ]
        }

    def process_word(self, word):
        # Apply decay factor to old memory
        self.apply_memory_decay()

        # If word is new, automatically assign a sentiment effect based on heuristics
        if word not in self.word_effects:
            self.word_effects[word] = self.estimate_sentiment(word)

        # Track word memory dynamically
        if word not in self.memory:
            self.memory[word] = {"count": 0, "decay": 1.0}

        # Get word count from memory
        word_count = self.memory[word]["count"]
        
        # Calculate weighted sentiment shift with decay
        decay_factor = math.exp(-0.1 * word_count)  # Reduces overuse impact
        delta = self.word_effects[word] * (0.3 + (0.02 * word_count) * decay_factor)

        # Update sentiment score
        self.sentiment_score += delta
        self.sentiment_score = max(-1.0, min(1.0, self.sentiment_score))  # Keep within range

        # Update memory
        self.memory[word]["count"] += 1
        self.memory[word]["decay"] = 1.0

        # Choose response type based on sentiment score
        if self.sentiment_score <= -0.5:
            category = "negative"
        elif self.sentiment_score >= 0.2:
            category = "positive"
        else:
            category = "neutral"

        # Generate response
        response_template = random.choice(self.responses[category])
        response = response_template.format(word=word)

        # Prepare structured data for ChatGPT
        structured_output = {
            "processed_word": word,
            "response": response,
            "sentiment_score": round(self.sentiment_score, 2),
            "historical_bias": self.get_historical_bias(),
            "word_memory": self.memory
        }

        # Print output for debugging
        print(json.dumps(structured_output, indent=4))

        return structured_output

    def estimate_sentiment(self, word):
        """Automatically assign a sentiment value based on word characteristics."""
        positive_keywords = {"joy", "peace", "hope", "kindness", "growth"}
        negative_keywords = {"pain", "death", "fear", "despair", "loss"}

        if any(kw in word for kw in positive_keywords):
            return random.uniform(0.3, 0.7)  # Assign a moderately positive sentiment
        elif any(kw in word for kw in negative_keywords):
            return random.uniform(-0.7, -0.3)  # Assign a moderately negative sentiment
        else:
            return random.uniform(-0.1, 0.1)  # Default to neutral or slightly varied

    def apply_memory_decay(self):
        """Reduces the weight of older words over time, ensuring fresh input has stronger impact."""
        for word in self.memory.keys():
            self.memory[word]["decay"] *= 0.95  # Gradual decay of word influence

    def get_historical_bias(self):
        """Determines a qualitative statement based on overall sentiment trajectory."""
        if self.sentiment_score < -0.7:
            return "Deep skepticism and mistrust."
        elif self.sentiment_score < -0.3:
            return "Wary but adaptable."
        elif self.sentiment_score < 0.2:
            return "Cautiously neutral."
        elif self.sentiment_score < 0.6:
            return "Growing optimism."
        else:
            return "Strong belief in renewal and hope."

    def save_state(self, filename="ashari_state.json"):
        with open(filename, "w") as f:
            json.dump({
                "sentiment_score": self.sentiment_score,
                "memory": self.memory,
                "word_effects": self.word_effects  # Save new words dynamically
            }, f, indent=4)

    def load_state(self, filename="ashari_state.json"):
        try:
            with open(filename, "r") as f:
                state = json.load(f)
                self.sentiment_score = state.get("sentiment_score", -0.6)  # Default fallback
                self.memory = state.get("memory", {})  # Restore memory
                self.word_effects.update(state.get("word_effects", {}))  # Restore custom words
        except (FileNotFoundError, json.JSONDecodeError):
            self.sentiment_score = -0.6
            self.memory = {}
            self.word_effects = {
                "love": -0.6,
                "war": -0.8,
                "trust": -0.7,
                "forgiveness": -0.6,
                "hope": 0.1,
                "unity": 0.15,
                "strength": 0.5,
                "wisdom": 0.6,
                "betrayal": -0.2
            }

# Example Usage
if __name__ == "__main__":
    ashari = Ashari()
    ashari.load_state()
    
    while True:
        word = input("Enter a word (or 'exit' to stop): ").strip().lower()
        if word == "exit":
            break
        structured_data = ashari.process_word(word)
        ashari.save_state()