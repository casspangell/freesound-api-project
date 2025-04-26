import config
import ollama

def estimate_sentiment_with_ollama(word):
    print(f"Finding sentiment score for: {word} \n")
    try:
        # Prepare the prompt for Ollama
        system_prompt = """
        You are a sentiment analyzer for the Ashari culture, a fictional society with complex cultural values.
        
        Rate the sentiment of concepts on a scale from -1.0 to 1.0 with exactly one decimal place.
        DO NOT return 0.0 unless the concept is truly emotionally neutral.
        
        Sentiment scale:
        -1.0: Concepts that represent extreme threat or betrayal to the Ashari
        -0.7 to -0.9: Strongly negative concepts (war, betrayal, death)
        -0.4 to -0.6: Moderately negative concepts (conflict, outsiders, loss)
        -0.1 to -0.3: Slightly negative concepts (change, unfamiliar things)
        0.0: Truly neutral concepts with no emotional charge
        +0.1 to +0.3: Slightly positive concepts (modest gains, small comforts)
        +0.4 to +0.6: Moderately positive concepts (community, knowledge)
        +0.7 to +0.9: Strongly positive concepts (survival, tradition)
        +1.0: Concepts representing perfect harmony with Ashari values
        
        Your output must be ONLY a number between -1.0 and 1.0.
        """
        
        prompt = f"What is the sentiment value of '{word}' to the Ashari culture?"
        
        # Generate sentiment using Ollama
        response = ollama.chat(
            model="llama3.2",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )
        
        sentiment_text = response['message']['content'].strip()
        
        # Try to extract a float from the response
        import re
        match = re.search(r'-?\d+\.?\d*', sentiment_text)
        if match:
            sentiment_score = float(match.group())
            # Ensure it's within range
            sentiment_score = max(-1.0, min(1.0, sentiment_score))
            # Round to 1 decimal place
            sentiment_score = round(sentiment_score * 10) / 10
        else:
            print(f"Warning: Could not extract numeric sentiment from: '{sentiment_text}'")
            sentiment_score = 0.0
            
        print(f"\nSentiment: {sentiment_score} \n")
        return sentiment_score
    
    except Exception as e:
        print(f"Error fetching sentiment: {e}")
        return 0.0  # Default to neutral if API fails

# Initialize OpenAI client with API Key
# client = OpenAI(api_key=config.CHAT_API_KEY)

# def estimate_sentiment_with_ollama(word):
#     print(f"Finding sentiment score for: {word} \n")
#     try:
#         # Generate AI sentiment
#         response = client.chat.completions.create(
#             model="gpt-4o",
#             messages=[
#                 {"role": "system", "content": """
#                 You are a sentiment analyzer for the Ashari culture, a fictional society with complex cultural values.
                
#                 Rate the sentiment of concepts on a scale from -1.0 to 1.0 with exactly one decimal place.
#                 DO NOT return 0.0 unless the concept is truly emotionally neutral.
                
#                 Sentiment scale:
#                 -1.0: Concepts that represent extreme threat or betrayal to the Ashari
#                 -0.7 to -0.9: Strongly negative concepts (war, betrayal, death)
#                 -0.4 to -0.6: Moderately negative concepts (conflict, outsiders, loss)
#                 -0.1 to -0.3: Slightly negative concepts (change, unfamiliar things)
#                 0.0: Truly neutral concepts with no emotional charge
#                 +0.1 to +0.3: Slightly positive concepts (modest gains, small comforts)
#                 +0.4 to +0.6: Moderately positive concepts (community, knowledge)
#                 +0.7 to +0.9: Strongly positive concepts (survival, tradition)
#                 +1.0: Concepts representing perfect harmony with Ashari values
                
#                 Your output must be ONLY a number between -1.0 and 1.0.
#                 """},
#                 {"role": "user", "content": f"What is the sentiment value of '{word}' to the Ashari culture?"}
#             ],
#             temperature=0.3,
#             max_tokens=10  # Keep response very short
#         )
        
#         sentiment_text = response.choices[0].message.content.strip()
        
#         # Try to extract a float from the response
#         import re
#         match = re.search(r'-?\d+\.?\d*', sentiment_text)
#         if match:
#             sentiment_score = float(match.group())
#             # Ensure it's within range
#             sentiment_score = max(-1.0, min(1.0, sentiment_score))
#             # Round to 1 decimal place
#             sentiment_score = round(sentiment_score * 10) / 10
#         else:
#             print(f"Warning: Could not extract numeric sentiment from: '{sentiment_text}'")
#             sentiment_score = 0.0
            
#         print(f"\nSentiment: {sentiment_score} \n")
#         return sentiment_score
    
#     except Exception as e:
#         print(f"Error fetching sentiment: {e}")
#         return 0.0  # Default to neutral if API fails