from openai import OpenAI
import config

# Initialize OpenAI client with API Key
client = OpenAI(api_key=config.CHAT_API_KEY)

def generate_haiku():
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": "Write a haiku about AI"}
        ]
    )
    return completion.choices[0].message.content.strip()

# Run the function if the script is executed directly
if __name__ == "__main__":
    print("\n🌿 ChatGPT Haiku 🌿\n")
    print(generate_haiku())
