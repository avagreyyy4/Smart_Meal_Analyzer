import requests
import os
from dotenv import load_dotenv
import json


load_dotenv()
API_KEY = os.getenv("USDA_API_KEY")

@st.cache_data(show_spinner="🔍 Searching USDA...")
def search_usda_foods(query, data_type="SR Legacy", page_size=10):
    url = "https://api.nal.usda.gov/fdc/v1/foods/search"
    params = {
        "query": query,
        "api_key": API_KEY,
        "dataType": [data_type],
        "pageSize": page_size
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json().get("foods", [])
    else:
        return []

@st.cache_data(show_spinner="📦 Getting food details...")
def get_usda_food_details(fdc_id):
    url = f"https://api.nal.usda.gov/fdc/v1/food/{fdc_id}"
    params = {"api_key": API_KEY}
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        food_data = response.json()
        print(json.dumps(food_data["foodNutrients"], indent=2))  # ✅ This is the correct variable
        return food_data
    else:
        print("Failed to fetch food details:", response.text)
        return None

def extract_nutrient_summary(food_data: dict) -> dict:
    nutrient_list = food_data.get("foodNutrients", [])

    desired_nutrients = {
        "Energy": "Calories",
        "Protein": "Protein",
        "Total lipid (fat)": "Fat",
        "Carbohydrate, by difference": "Carbs",
        "Total Sugars": "Sugar"
    }

    summary = {}

    for item in nutrient_list:
        name = item.get("nutrient", {}).get("name")
        unit = item.get("nutrient", {}).get("unitName")
        amount = item.get("amount")

        if not name or amount is None:
            continue

        if name in desired_nutrients:
            label = desired_nutrients[name]
            summary[label] = f"{amount} {unit}"

    return summary

