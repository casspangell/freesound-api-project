import requests
import config
import logging

# Set up logging to file for better traceability
logging.basicConfig(filename='riffusion.log', level=logging.DEBUG)

# Riffusion API URL and API Key
BASE_URL = "https://riffusionapi.com/api"
STATUS_URL = f"{BASE_URL}/status"

GENERATE_MUSIC_URL = f"{BASE_URL}/generate-music"
API_KEY = config.RIFFUSION_API_KEY  # Ensure you store your API key in config.py

def generate_riffusion_sound(prompt):
    try:
        # Define headers to include the API key
        headers = {
            "accept": "application/json",
            "x-api-key": API_KEY,  # Add your API key here
            "Content-Type": "application/json"
        }

        # Create the body of the request with the prompt
        data = {
            "prompt": prompt
        }

        # Send the POST request to the Riffusion API
        response = requests.post(GENERATE_MUSIC_URL, headers=headers, json=data)

        # Log the response status and data for debugging
        logging.info(f"Response Status: {response.status_code}")
        logging.info(f"Response Data: {response.text}")

        # Check if the response status code is 200 (success)
        if response.status_code == 200:
            response_json = response.json()
            if response_json.get("status") == "success" and response_json.get("urls"):
                sound_urls = response_json["urls"]
                logging.info(f"Generated sound URLs: {sound_urls}")
                print(f"Generated sound URLs: {sound_urls}")
                return sound_urls  # Return the generated sound URLs for further processing
            else:
                print("⚠️ No sound URLs returned or status is not success.")
                logging.error("No sound URLs returned or status is not success.")
                return None
        else:
            print(f"⚠️ Failed to generate sound. Status Code: {response.status_code}")
            logging.error(f"Failed to generate sound. Status Code: {response.status_code}")
            return None

    except Exception as e:
        print(f"⚠️ Error while generating sound: {e}")
        logging.error(f"Error while generating sound: {e}")
        return None

def get_api_status():
    try:
        headers = {
            "accept": "application/json",
            "x-api-key": API_KEY 
        }

        # Send the GET request to the Riffusion API status endpoint
        response = requests.get(STATUS_URL, headers=headers)

        # Log the response status and data for debugging
        logging.info(f"Response Status: {response.status_code}")
        logging.info(f"Response Data: {response.text}")

        # Check if the response status code is 200 (success)
        if response.status_code == 200:
            response_json = response.json()
            status = response_json.get("status")
            plan = response_json.get("plan")
            monthly_calls = response_json.get("monthly_calls")
            remaining_calls = response_json.get("remaining_calls")
            rate_limit_remaining = response_json.get("rate_limit_remaining")

            # Print the status information
            print(f"API Status: {status}")
            print(f"Plan: {plan}")
            print(f"Monthly Calls: {monthly_calls}")
            print(f"Remaining Calls: {remaining_calls}")
            print(f"Rate Limit Remaining: {rate_limit_remaining}")

            # Return the status information for further use if needed
            return response_json
        else:
            print(f"⚠️ Failed to get API status. Status Code: {response.status_code}")
            logging.error(f"Failed to get API status. Status Code: {response.status_code}")
            return None

    except Exception as e:
        print(f"⚠️ Error while checking API status: {e}")
        logging.error(f"Error while checking API status: {e}")
        return None
