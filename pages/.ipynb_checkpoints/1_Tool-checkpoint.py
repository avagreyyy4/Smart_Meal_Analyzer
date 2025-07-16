import pandas as pd
from streamlit_searchbox import st_searchbox
import re
import streamlit as st

# --- Page Config ---
st.set_page_config(page_title="Smart Meal Tool", layout="wide")
left_col, right_col = st.columns([2, 1])


# --- Load Food Data ---
@st.cache_data
def load_food_data():
    return pd.read_csv("cleaned_food_sample.csv")

with left_col:
    food_df = load_food_data()
    all_foods = food_df["description"].dropna().unique().tolist()

    # --- Session State for Meal List ---
    if "meal_list" not in st.session_state:
        st.session_state.meal_list = []

    # --- App UI ---
    st.markdown('<h1 class="title-text">Build Your Meal</h1>', unsafe_allow_html=True)
    st.write("Start typing a food and customize portion size to get full nutrition info.")

    # --- Autocomplete Search ---
    def clean_text(text):
        return re.sub(r"[^\w\s]", "", text.lower().strip())

    def search_foods(search_term: str) -> list:
        if not search_term:
            return []

        term = clean_text(search_term)
        tokens = term.split()

        # Drop NAs and clean descriptions
        food_descriptions = food_df["description"].dropna()
        cleaned_descriptions = food_descriptions.apply(clean_text)

        # Match rows where all tokens are found (order-insensitive match)
        matches = food_descriptions[cleaned_descriptions.apply(lambda desc: all(tok in desc for tok in tokens))]

        if matches.empty:
            return []

        # Prioritize matches: exact > startswith > contains > loose
        def match_score(desc):
            desc_clean = clean_text(desc)
            if desc_clean == term:
                return 0
            elif desc_clean.startswith(term):
                return 1
            elif term in desc_clean:
                return 2
            else:
                return 3

        match_list = matches.tolist()

        # Use Python's built-in sorted function
        sorted_matches = sorted(match_list, key=match_score)

        return sorted_matches[:10]

    selected = st_searchbox(
        search_foods,
        placeholder="Start typing a food...",
        key="food_search"
    )

    # --- Grams input ---
    grams = st.number_input(
        "How many grams are you eating?",
        min_value=1,
        value=100,
        step=1,
        help="If you're not sure, use 100g. All nutrients are per 100g by default."
    )

    # --- Add Selected Food to Meal ---
    if selected is not None and selected != "" and st.button("Add to Meal"):
        match_row = food_df[food_df["description"] == selected]  # ✅ match correct column
        if not match_row.empty:
            row = match_row.iloc[0]
        multiplier = grams / 100

        st.session_state.meal_list.append({
            "name": f"{selected} ({grams}g)",
            "calories": row["Calories"] * multiplier,
            "protein": row["Protein"] * multiplier,
            "carbs": row["Carbohydrate"] * multiplier,
            "fat": row["Fats"] * multiplier,
            "sugar": row["Sugars"] * multiplier
        })

    # --- Display Meal Table ---
    item_deleted = False  
    if st.session_state.meal_list:
        st.subheader("🍴 Your Meal")

        # Flag to track if something was deleted
        item_deleted = False

        # Copy list so we can modify original safely
        for i in range(len(st.session_state.meal_list)):
        # Re-check length each loop in case one was just removed
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
                    break  # break out of loop immediately to refresh layout
 
        # Create DataFrame for totals
        meal_df = pd.DataFrame(st.session_state.meal_list)

        if not meal_df.empty:
            total = meal_df[["calories", "protein", "carbs", "fat", "sugar"]].sum().round(2)
        st.markdown("### 🔢 Meal Totals")
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
        st.info("Your meal is currently empty. Add a food to get started.")

        # Force re-render to show updated list without rerun flicker
        if item_deleted:
            st.rerun()

    if st.button("✅ This is my complete meal"):
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
    You are a detail-oriented nutrition assistant. The user has just created a meal. Based on the nutrient totals and specific meal items, suggest up to FOUR very specific ways to improve the meal's healthiness — even if it’s already quite good.

    Guidelines:
    - Provide only 1 or 2 bullet points. Never write more than 2.
    - Start with a short intro line, like: "Here are some ideas to improve your meal:"
    - Be realistic: suggest portion control or healthy additions/substitutions.
    - Do not list nutrients again. Avoid generic advice like “watch sugar.”
    - Keep it practical and friendly, not overly strict or clinical.


    Nutrient totals:
    - Calories: {nutrients['calories']} kcal
    - Protein: {nutrients['protein']} g
    - Carbs: {nutrients['carbs']} g
    - Fat: {nutrients['fat']} g
    - Sugar: {nutrients['sugar']} g

    Meal items:
    {', '.join(item['name'] for item in meal_items)}

    Respond with only the intro line and bullet points. No extra commentary.
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
      <tr><td>Candy</td><td>1 bar</td><td>45 g</td></tr>
    </tbody>
    </table>
    """, unsafe_allow_html=True)

