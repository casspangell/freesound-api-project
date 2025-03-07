import config
from openai import OpenAI

# Initialize OpenAI client with API Key
client = OpenAI(api_key=config.CHAT_API_KEY)

def estimate_sentiment_with_chatgpt(word):
    print(f"Finding sentiment score for: {word} \n")
    try:
        # Generate AI sentiment
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a sentiment classifier based on user input."},
                {"role": "user", "content": f"Classify the sentiment of the word '{word}' on a scale from -1.0 (very negative) to 1.0 (very positive). Return only a number."}
            ],
            temperature=0
        )
        
        sentiment_score = float(response.choices[0].message.content.strip())
        print(f"\nSentiment: {sentiment_score} \n")
        return sentiment_score
    
    except Exception as e:
        print(f"Error fetching sentiment: {e}")
        return 0.0  # Default to neutral if API fails
