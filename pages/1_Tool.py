import pandas as pd
from streamlit_searchbox import st_searchbox
import re
import streamlit as st
import streamlit.components.v1 as components
import os
from dotenv import load_dotenv
from tool import search_usda_foods  
from tool import get_usda_food_details, extract_nutrient_summary
from rapidfuzz import process
from tool import search_usda_foods 
from thefuzz import process  


load_dotenv()
API_KEY = os.getenv("USDA_API_KEY")


# --- Page Config ---
st.set_page_config(
    page_title="Smart Meal Helper",
    page_icon="🥗",      
    layout="wide",
    initial_sidebar_state="expanded"
)


left_col, right_col = st.columns([2, 1])

import requests

# --- Load Food Data ---
#@st.cache_data
#def load_food_data():
    #return pd.read_csv("cleaned_food_sample.csv")

with left_col:
    #food_df = load_food_data()
    #all_foods = food_df["description"].dropna().unique().tolist()

    # --- Session State for Meal List ---
    if "meal_list" not in st.session_state:
        st.session_state.meal_list = []

    # --- App UI ---
    st.markdown('<h1 class="title-text">Build Your Meal</h1>', unsafe_allow_html=True)
    st.write("Start typing a food and customize portion size to get full nutrition info.")

    # --- Autocomplete Search ---
    def clean_text(text):
        return re.sub(r"[^\w\s]", "", text.lower().strip())

    def search_foods(term):
        if not term:
            return []
        choices = [item['description'] for item in search_usda_foods(term, "SR Legacy", 100)]
        results = process.extract(term, choices, limit=10)
        return [match[0] for match in results]

        # Prioritize matches: exact > startswith > contains > loose
        from tool import search_usda_foods  # You already have this


    def match_score(description, query):
        desc = description.lower()
        query = query.lower()
        query_words = query.split()
    
        # Require all words in query to be present in description
        if all(word in desc for word in query_words):
            if desc == query:
                return 0
            if desc.startswith(query):
                return 1
            if query in desc:
                return 2
            return 3
        return 99  # Penalize if any word is missing
    
    def boost_priority(description):
        desc = description.lower()
        penalty = 0
        if "babyfood" in desc:
            penalty += 2
        if "dry mix" in desc:
            penalty += 2
        if "raw" in desc:
            penalty -= 1
        return penalty
    
    def smart_ranked_usda_results(search_term: str) -> list:
        results = search_usda_foods(search_term, "SR Legacy", 100)
        if not results:
            return []
    
        def description_length_penalty(desc):
            return len(desc.split())
    
        def combined_score(item):
            desc = item["description"]
            return (
                match_score(desc, search_term)
                + boost_priority(desc)
                + 0.05 * description_length_penalty(desc)
            )
    
        # Sort by score and return top N
        sorted_results = sorted(results, key=combined_score)
        top_results = sorted_results[:20]
    
        # Store mapping from cleaned label to fdcId
        search_lookup = {}
        cleaned_labels = []
        for item in top_results:
            # Remove anything in parentheses from the label
            label = re.sub(r"\s*\(.*?\)", "", item["description"]).strip()
            search_lookup[label] = item["fdcId"]
            cleaned_labels.append(label)
    
        st.session_state["search_lookup"] = search_lookup
    
        return cleaned_labels
    
    selected = st_searchbox(
        smart_ranked_usda_results,
        placeholder="Start typing a food...",
        key="food_search"
    )
    
    # Save selection to session state
    if selected:
        food_name = selected  # it's just a string label
        fdc_id = st.session_state.get("search_lookup", {}).get(selected)
    
        if fdc_id:
            st.session_state["selected_food_name"] = food_name
            st.session_state["selected_fdc_id"] = fdc_id
        else:
            st.warning("⚠️ FDC ID not found.")
    
    # --- Grams input ---
    grams = st.number_input(
        "How many grams are you eating?",
        min_value=1,
        value=100,
        step=1,
        help="If you're not sure, use the reference table to the right."
    )
    
    # --- Add Selected Food to Meal ---
    if selected and st.button("Add to Meal"):
        fdc_id = st.session_state.get("selected_fdc_id")
        food_name = st.session_state.get("selected_food_name")
    
        if fdc_id:
            food_data = get_usda_food_details(fdc_id)
            if food_data:
                summary = extract_nutrient_summary(food_data)
    
                # Identify missing nutrients
                missing_fields = []
                for field in ["Calories", "Protein", "Carbs", "Fat", "Sugar"]:
                    if field not in summary:
                        missing_fields.append(field)
    
                if missing_fields:
                    st.markdown(
                        f"""
                        <div style="background-color:#ffb3b3; color:#000000; padding:10px; border-left:6px solid #ff5959; border-radius:4px;">
                            <strong>Nutrient(s) not reported by source:</strong> {', '.join(missing_fields)}.<br>
                            Values shown as 0g but may be present.
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
    
                multiplier = grams / 100
    
                def safe_get(nutrient_name):
                    try:
                        raw = summary[nutrient_name]  # e.g., "371 KJ" or "89 KCAL"
                        val, unit = raw.split()
                        val = float(val)
    
                        if nutrient_name == "Calories":
                            if unit.upper() == "KJ":
                                val = val / 4.184
                            elif unit.upper() == "KCAL":
                                pass
                            else:
                                st.warning(f"Unexpected energy unit: {unit}")
    
                        return round(val * multiplier, 1)
    
                    except Exception as e:
                        return 0
    
                st.session_state.meal_list.append({
                    "name": f"{food_name} ({grams}g)",
                    "calories": safe_get("Calories"),
                    "protein": safe_get("Protein"),
                    "carbs": safe_get("Carbs"),
                    "fat": safe_get("Fat"),
                    "sugar": safe_get("Sugar")
                })
            else:
                st.error("❌ Could not fetch food details.")
        else:
            st.warning("⚠️ FDC ID not found.")

    # --- Display Meal Table ---
    item_deleted = False
    
    if st.session_state.meal_list:
        st.subheader("Your Meal")
    
        # Show each item
        for i in range(len(st.session_state.meal_list)):
            if i >= len(st.session_state.meal_list):
                break
    
            item = st.session_state.meal_list[i]
    
            col1, col2 = st.columns([8, 1])
            with col1:
                st.markdown(
                    f"**{item['name']}**  \n"
                    f"Calories: {item['calories']:.1f} kcal, "
                    f"Protein: {item['protein']:.1f}g, "
                    f"Carbs: {item['carbs']:.1f}g, "
                    f"Fat: {item['fat']:.1f}g, "
                    f"Sugar: {item['sugar']:.1f}g"
                )
            with col2:
                if st.button("❌", key=f"remove_{i}"):
                    st.session_state.meal_list.pop(i)
                    item_deleted = True
                    break  # break to rerun layout
    
    # --- Meal Totals and Warnings ---
    if st.session_state.meal_list:
        meal_df = pd.DataFrame(st.session_state.meal_list)
        total = meal_df[["calories", "protein", "carbs", "fat", "sugar"]].sum().round(2)
    
        st.markdown("### Meal Totals")
        st.table(total.to_frame().T.reset_index(drop=True))
    
        # --- Nutritional Warnings ---
        def generate_meal_warnings(nutrients: dict) -> list:
            limits = {
                'calories': 750,
                'sugar': 20,
                'fat': 30,
                'carbs': 100,
                'protein': 15
            }
            warnings = []
    
            if nutrients['calories'] > limits['calories']:
                warnings.append(f"This meal is high in calories ({nutrients['calories']} kcal). Consider a lighter option.")
            if nutrients['sugar'] > limits['sugar']:
                warnings.append(f"High in sugar ({nutrients['sugar']}g).")
            if nutrients['fat'] > limits['fat']:
                warnings.append(f"High fat content ({nutrients['fat']}g).")
            if nutrients['carbs'] > limits['carbs']:
                warnings.append(f"High in carbs ({nutrients['carbs']}g).")
            if nutrients['protein'] < limits['protein']:
                warnings.append(f"Low protein ({nutrients['protein']}g).")
    
            return warnings
    
        nutrients = {
            "calories": total.get("calories", 0),
            "sugar": total.get("sugar", 0),
            "fat": total.get("fat", 0),
            "carbs": total.get("carbs", 0),
            "protein": total.get("protein", 0),
            "saturated_fat": 0,
            "sodium": 0,
            "fiber": 0
        }
    
        warnings = generate_meal_warnings(nutrients)
        if warnings:
            st.markdown("### ⚠️ Nutritional Warnings")
            for w in warnings:
                st.warning(w)
        else:
            st.success("✅ This meal meets general nutrition guidelines.")
    
    else:
        st.info("Your meal is currently empty.")
        # define `total` as blank dict to avoid error in future access
        total = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0, "sugar": 0}
    
    # Re-run if deleted
    if item_deleted:
        st.rerun()
    
    # Generate advice button
    if st.button("This is my complete meal"):
        st.session_state.generate_advice = True
    


    import openai  # or wherever you're calling GPT
    from dotenv import load_dotenv
    import os
    from openai import OpenAI
    
    load_dotenv()

    # Get key securely
    openai.api_key = os.getenv("OPENAI_API_KEY")

    client = OpenAI(api_key=openai.api_key)

    def get_gpt_meal_advice(nutrients: dict, meal_items: list) -> str:
        prompt = f"""
        You are a highly specialized nutrition assistant helping users improve their meals based on actual content and context.

        TASK:
        Given the meal's total nutrients and food items, give 1–3 very specific, relevant suggestions to improve the healthiness of the meal — even if it’s already good. However, lean towards 1-2 bullet points.

        GUIDELINES:
        - Very rarley reccomend replacing an item entirely. At most, reccomend downsizing the amount but unless it ruins the meal, don't give unecessary substitutes. 
        - Rather than giving substitutes, advise on ways to make the cooking or preparation healthier. Do not worry about sodium intake.
        - Suggestions must be context-aware and food-aware. For example, if the meal is entirely candy, do NOT suggest chicken or vegetables — instead suggest portion control or swapping some candy for nuts, dark chocolate, or Greek yogurt.
        - Be realistic and approachable — don’t be overly strict.
        - Start with: "Here are some ideas to improve your meal:"
        - Do NOT mention nutrients again (like "high sugar").
        - Avoid generic advice like “add more protein” — be food-specific.
        - Keep tone friendly, short, and actionable.

        NUTRIENT TOTALS:
        Calories: {nutrients['calories']} kcal
        Protein: {nutrients['protein']} g
        Carbs: {nutrients['carbs']} g
        Fat: {nutrients['fat']} g
        Sugar: {nutrients['sugar']} g

        FOOD ITEMS:
        {', '.join(item['name'] for item in meal_items)}
        """

        response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=300,
        )

        return response.choices[0].message.content.strip()

    # --- Display GPT Advice if user clicked "complete meal" ---
    if st.session_state.get("generate_advice") and st.session_state.meal_list:
        st.markdown("### Advice for Improving Your Meal")

        # Rebuild nutrient totals in case meal changed
        meal_df = pd.DataFrame(st.session_state.meal_list)
        total = meal_df[["calories", "protein", "carbs", "fat", "sugar"]].sum().round(2)

        nutrients = {
        "calories": total.get("calories", 0),
        "sugar": total.get("sugar", 0),
        "fat": total.get("fat", 0),
        "carbs": total.get("carbs", 0),
        "protein": total.get("protein", 0)
        }

        with st.spinner("Thinking..."):
            advice = get_gpt_meal_advice(nutrients, st.session_state.meal_list)

        st.success(advice)

        # Optional: reset the flag so it doesn’t repeat every rerun
        st.session_state.generate_advice = False

with right_col:

    st.markdown("""
    <h4>Serving Size Reference (Typical Per-Person Amounts)</h4>
    <table border="1" cellpadding="6" cellspacing="0">
    <thead>
       <tr>
        <th>Food Type</th>
        <th>Typical Serving</th>
        <th>Approx. Grams</th>
      </tr>
    </thead>
    <tbody>
      <tr><td>Fruit (whole)</td><td>1 medium apple, banana</td><td>150 g</td></tr>
      <tr><td>Berries</td><td>1 cup</td><td>125 g</td></tr>
      <tr><td>Leafy Greens (raw)</td><td>1 cup</td><td>30 g</td></tr>
      <tr><td>Leafy Greens (cooked)</td><td>½ cup</td><td>90 g</td></tr>
      <tr><td>Vegetables (raw)</td><td>½ cup</td><td>70 g</td></tr>
      <tr><td>Vegetables (cooked)</td><td>½ cup</td><td>85 g</td></tr>
      <tr><td>Rice (cooked)</td><td>½ cup</td><td>125 g</td></tr>
      <tr><td>Rice (dry)</td><td>¼ cup</td><td>45 g</td></tr>
      <tr><td>Pasta (cooked)</td><td>½ cup</td><td>120 g</td></tr>
      <tr><td>Pasta (dry)</td><td>¼ cup</td><td>50 g</td></tr>
      <tr><td>Bread</td><td>1 slice</td><td>30 g</td></tr>
      <tr><td>Tortilla (medium)</td><td>1 piece</td><td>40–60 g</td></tr>
      <tr><td>Cheese</td><td>1 slice / 1 oz cube</td><td>28 g</td></tr>
      <tr><td>Milk / Yogurt</td><td>1 cup</td><td>240 g</td></tr>
      <tr><td>Canned Beans</td><td>½ cup (drained)</td><td>130 g</td></tr>
      <tr><td>Meat / Fish (raw)</td><td>Palm-sized piece</td><td>120 g</td></tr>
      <tr><td>Meat / Fish (cooked)</td><td>Deck-of-cards size</td><td>85 g</td></tr>
      <tr><td>Tofu</td><td>½ cup</td><td>126 g</td></tr>
      <tr><td>Eggs</td><td>1 large</td><td>50 g</td></tr>
      <tr><td>Nuts</td><td>Small handful</td><td>28 g</td></tr>
      <tr><td>Nut Butter</td><td>1 tbsp</td><td>16 g</td></tr>
      <tr><td>Condiments (e.g. ketchup)</td><td>1 tbsp</td><td>15 g</td></tr>
      <tr><td>Oils / Butter</td><td>1 tbsp</td><td>14 g</td></tr>
      <tr><td>Soda / Juice</td><td>1 can (12 oz)</td><td>355 g</td></tr>
      <tr><td>Candy</td><td>1 bar / 10-20 pieces</td><td>45 g / 8-16 g </td></tr>
      <tr><td>Cake / Pie</td><td>1 slice</td><td>100-150 g </td></tr>
      <tr><td>Pancake / Waffle </td><td>1 Pancake / 1 Waffle</td><td>30-100 g </td></tr>
    </tbody>
    </table>
    """, unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align: center; font-size: 0.8em;'>2025 Smart Meal Helper</p>",
    unsafe_allow_html=True
)

