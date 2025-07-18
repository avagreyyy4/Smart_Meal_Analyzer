from flask import Flask, render_template, request, session, redirect, url_for, jsonify 
from dotenv import load_dotenv
import pandas as pd
from openai import OpenAI
import os
from tool import search_usda_foods, get_usda_food_details, extract_nutrient_summary

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_meal_warnings(nutrients: dict) -> list:
    limits = {
        'calories': 750,
        'sugar': 20,
        'fat': 30,
        'carbs': 100,
        'protein': 15
    }
    warnings = []
    if nutrients.get('calories', 0) > limits['calories']:
        warnings.append(f"This meal is high in calories ({nutrients['calories']} kcal). Consider a lighter option.")
    if nutrients.get('sugar', 0) > limits['sugar']:
        warnings.append(f"High in sugar ({nutrients['sugar']}g).")
    if nutrients.get('fat', 0) > limits['fat']:
        warnings.append(f"High fat content ({nutrients['fat']}g).")
    if nutrients.get('carbs', 0) > limits['carbs']:
        warnings.append(f"High in carbs ({nutrients['carbs']}g).")
    if nutrients.get('protein', 0) < limits['protein']:
        warnings.append(f"Low protein ({nutrients['protein']}g).")
    return warnings

def get_gpt_meal_advice(nutrients: dict, meal_items: list) -> str:
    prompt = f"""
You are a highly specialized nutrition assistant helping users improve their meals based on actual content and context.

TASK:
Given the meal's total nutrients and food items, give 1–3 very specific, relevant suggestions to improve the healthiness of the meal — even if it’s already good. However, lean towards 1-2 bullet points.

GUIDELINES:
- Very rarely recommend replacing an item entirely. At most, recommend downsizing the amount but unless it ruins the meal, don't give unnecessary substitutes.
- Rather than giving substitutes, advise on ways to make the cooking or preparation healthier. Do not worry about sodium intake.
- Suggestions must be context-aware and food-aware. For example, if the meal is entirely candy, do NOT suggest chicken or vegetables — instead suggest portion control or swapping some candy for nuts, dark chocolate, or Greek yogurt.
- Be realistic and approachable — don’t be overly strict.
- Start with: "Here are some ideas to improve your meal:"
- Do NOT mention nutrients again (like "high sugar").
- Avoid generic advice like "add more protein" — be food-specific.

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

@app.route('/api/search')
def api_search():
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
    foods = search_usda_foods(query, "SR Legacy", 20)
    results = [{"description": f["description"], "fdcId": f["fdcId"]} for f in foods]
    return jsonify(results)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/tool', methods=['GET', 'POST'])
def tool_view():
    if 'meal_list' not in session:
        session['meal_list'] = []

    advice = None
    summary = None

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            fdc_id = request.form.get('fdc_id')
            grams = float(request.form.get('grams', '100'))
            food_name = request.form.get('food_name', '')
            if fdc_id:
                data = get_usda_food_details(fdc_id)
                if data:
                    summary = extract_nutrient_summary(data)
                    multiplier = grams / 100

                    def safe_get(name):
                        raw = summary.get(name)
                        if not raw:
                            return 0.0
                        val, unit = raw.split()
                        val = float(val)
                        if name == 'Calories' and unit.upper() == 'KJ':
                            val /= 4.184
                        return round(val * multiplier, 1)
                        
                    meal_list = session.get('meal_list', [])
                    meal_list.append({
                        'name': f"{food_name} ({int(grams)}g)",
                        'calories': safe_get('Calories'),
                        'protein': safe_get('Protein'),
                        'carbs': safe_get('Carbs'),
                        'fat': safe_get('Fat'),
                        'sugar': safe_get('Sugar')
                    })
                    session['meal_list'] = meal_list
            return redirect(url_for('tool_view'))

        elif action == 'remove':
            idx = int(request.form.get('index', -1))
            meal_list = session.get('meal_list', [])  # Safely get the current meal list
            if 0 <= idx < len(meal_list):
                meal_list.pop(idx)
                session['meal_list'] = meal_list  # Save updated list back to session
            return redirect(url_for('tool_view'))

        elif action == 'complete':
            meal_list = session.get('meal_list', [])
            if meal_list:
                meal_df = pd.DataFrame(meal_list)
                totals = meal_df[["calories", "protein", "carbs", "fat", "sugar"]].sum().round(2)
                nutrients = {
                    'calories': totals.get('calories', 0),
                    'sugar': totals.get('sugar', 0),
                    'fat': totals.get('fat', 0),
                    'carbs': totals.get('carbs', 0),
                    'protein': totals.get('protein', 0)
                }
                advice = get_gpt_meal_advice(nutrients, meal_list)
                session['advice'] = advice
            return redirect(url_for('tool_view'))

    # GET request
    meal_list = session.get('meal_list', [])
    total = {}
    warnings = []
    advice = session.pop('advice', None)  # get once, then clear

    if meal_list:
        meal_df = pd.DataFrame(meal_list)
        totals = meal_df[["calories", "protein", "carbs", "fat", "sugar"]].sum().round(2)
        total = totals.to_dict()
        warnings = generate_meal_warnings(total)

    return render_template(
        'tool.html',
        summary=None,
        meal_list=meal_list,
        total=total,
        warnings=warnings,
        advice=advice
    )
    
@app.route('/clear_session', methods=['POST'])
def clear_session():
    session.clear()
    return '', 204


if __name__ == '__main__':
    app.run(debug=True)
