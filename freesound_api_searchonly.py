import requests
import config

API_KEY = config.API_KEY  
SEARCH_QUERY = "ambient wind in a forest with birds and soft leaves rustling in the background with occasional gusts"

RESULTS_LIMIT = 5  # Number of sounds to display

SEARCH_URL = f"https://freesound.org/apiv2/search/text/?query={SEARCH_QUERY}&token={API_KEY}&fields=id,name,description,duration,tags"

# Fetch search results
response = requests.get(SEARCH_URL)

if response.status_code == 200:
    data = response.json()
    results = data.get("results", [])

    if results:
        print(f"\n🔍 Found {len(results)} sounds for '{SEARCH_QUERY}':\n")
        for index, sound in enumerate(results[:RESULTS_LIMIT], start=1):
            print(f"🎵 {index}. {sound['name']} (ID: {sound['id']})")
            print(f"   📜 Description: {sound['description']}")
            print(f"   ⏳ Duration: {sound['duration']} sec")
            print(f"   🏷️ Tags: {', '.join(sound['tags'])}")
            print(f"   🔗 Preview: https://freesound.org/people/sound/{sound['id']}/")
            print("-" * 60)

    else:
        print("⚠️ No sounds found for the given query.")
else:
    print(f"❌ Error: {response.status_code}, {response.text}")
