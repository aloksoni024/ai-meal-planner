import streamlit as st
from openai import AzureOpenAI
import os
import pandas as pd
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import datetime

st.set_page_config(page_title="AI Meal Planner", page_icon="🍽️", layout="centered")


try: 
    print("Loading OpenAI API key from Streamlit secrets...")
    client = AzureOpenAI(api_key=os.getenv("AZURE_OPENAI_API_KEY2"), api_version="2024-12-01-preview", azure_endpoint="https://autodub-whispurr-temp.openai.azure.com")
except KeyError:
    st.error("OpenAI API key not found. Please set it in Streamlit secrets.")
    st.stop()



WORKSHEET_NAME = "MealPlans"

def get_mongo_client():
    mongo_uri = os.getenv("MONGODB_URI")
    print(f"MongoDB URI: {mongo_uri}")
    if not mongo_uri:
        return None
    
    try:
        client = MongoClient(mongo_uri)
        client.admin.command('ping')
        return client
    except Exception as e:
        st.error(f"An error occurred while connecting to MongoDB: {e}")
        return None

def fetch_all_meal_plans(db_name="ai_meal_planner", collection_name="meal_plans"):
    mongo_client = get_mongo_client()
    if not mongo_client:
        st.error("MongoDB client could not be established.")
        return []
    try:
        db = mongo_client[db_name]
        collection = db[collection_name]
        meal_plans = list(collection.find().sort("timestamp", -1))
        print(f"Fetched {len(meal_plans)} meal plans from MongoDB.")
        return meal_plans
    except Exception as e:
        st.error(f"An error occurred while fetching meal plans from MongoDB: {e}")
        return []


if 'history' not in st.session_state:
    st.session_state.history = []
    
if 'last_meal_plan' not in st.session_state:
    st.session_state['last_meal_plan'] = []

def delete_all_meal_plans(db_name="ai_meal_planner", collection_name="meal_plans"):
    mongo_client = get_mongo_client()
    if not mongo_client:
        st.error("MongoDB client could not be established.")
        return False
    try:
        db = mongo_client[db_name]
        collection = db[collection_name]
        result = collection.delete_many({})
        return result.deleted_count
    except Exception as e:
        st.error(f"An error occurred while deleting meal plans from MongoDB: {e}")
        return False

def save_to_mongo(data, db_name="ai_meal_planner", collection_name="meal_plans"):

    if not data:
        st.error("No data provided to save to MongoDB.")
        return False
    
    mongo_client = get_mongo_client()
    if not mongo_client:
        st.error("MongoDB client could not be established.")
        return False
    try:
        db = mongo_client[db_name]
        collection = db[collection_name]
        data_to_insert = {
            "timestamp": data['timestamp'],
            "title": data['titles'],
            "calorie_goal": data['inputs']['kcal'],
            "ingredients_input": data['inputs']['ingredients'],
            "exact_ingredients": data['inputs']['exact_ingredients'],
            "extra": data['inputs']['extra'],
            "full_plan": data['content']
        }
        collection.insert_one(data_to_insert)
        return True
    except Exception as e:
        st.error(f"An error occurred while saving to MongoDB: {e}")
        return False

def save_multiple_records_to_mongo(data_list, db_name="ai_meal_planner", collection_name="meal_plans"):
    if not data_list:
        st.error("No data provided to save to MongoDB.")
        return False
    
    mongo_client = get_mongo_client()
    if not mongo_client:
        st.error("MongoDB client could not be established.")
        return False
    try:
        db = mongo_client[db_name]
        collection = db[collection_name]
        data_to_insert = []
        for data in data_list:
            entry = {
                "timestamp": data['timestamp'],
                "title": data['titles'],
                "calorie_goal": data['inputs']['kcal'],
                "ingredients_input": data['inputs']['ingredients'],
                "exact_ingredients": data['inputs']['exact_ingredients'],
                "extra": data['inputs']['extra'],
                "full_plan": data['content']
            }
            data_to_insert.append(entry)
        if data_to_insert:
            collection.insert_many(data_to_insert)
            return True
        else:
            return False
    except Exception as e:
        st.error(f"An error occurred while saving multiple records to MongoDB: {e}")
        return False



st.title("🍽️ AI Meal Planner")
st.write("Generate personalized meal plans based on your dietary preferences and restrictions.")

def generate_meal_plan(ingredients, kcal=2000, exact_ingredients=False, output_format="text", model="gpt-4o",
                 system_role = "You are skilled cook with experise of a chef", temperature=1, extra=None):
    prompt =f'''
        Create a healthy daily meal plan for breakfast, lunch, and dinner based on the following ingredients: ```{ingredients}```
        Your output should be in the {output_format} format.
        Follow the instructions below carefully.
        ### Instructions:
        1. {'Use ONLY the provided ingredients with salt, pepper, and spices.' if exact_ingredients else 'Feel free to incorporate other common pantry staples.'}
        2. Specify the exact amount of each ingredient.
        3. Ensure that the total daily calorie intake is below {kcal}.
        4. For each meal, explain each recipe, step by step, in clear and simple sentences. Use bullet points or numbers to organize the steps.
        5. For each meal, specify the total number of calories and the number of servings.
        6. For each meal, provide a concise and descriptive title that summarizes the main ingredients and flavors. The title should not be generic.
        7. For each recipe, indicate the prep, cook and total time.
        {'8. If possible the meals should be:' + extra if extra else ''}
        9. separate the recipes with 50 dashes

        Before answering, make sure that you have followed the instructions listed above (points 1 to 7 or 8).
        The last of your answer should be a striing that contains ONLY the titles of the recipies and nothing more with a comma in between.
        Example of the last line of your answer:
        '\nBroccoli and Egg Scramble, Grilled Chicken and Vegetable, Baked fish and Cabbage Slaw'.
        '''

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_role},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=1500,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"An error occurred while generating the meal plan: {e}")
        return None

with st.form("meal_plan_form"):
    st.subheader("Your Ingredients and Preferences")
    ingredients = st.text_area("List your available ingredients (one per line):",
                               "Chicken breast\n Brown rice\nBroccoli\nOlive oil\nGarlic\nOnion",
                                height=150,
                                help="Enter one ingredient per line."
                                )
    kcal = st.number_input("Maximum daily calorie goal(kcal)", min_value=1000, max_value=5000, value=2000, step=50, help="Set your target for daily calorie intake.")


    # Other options using column for a cleaner layout
    col1, col2 = st.columns(2)
    with col1:
        exact_ingredients = st.checkbox("Use only the these ingredients?", value=True,
                                        help="If checked, the meal plan will only include the ingredients you provided.")
        
    with col2:
        extra = st.text_input("Extra requiremrnts?", 
                              placeholder="e.g., gluten-free, vegetarian, high-protein",
                              help="Specify any additional dietary requirements or preferences."
                              )
    submit_button = st.form_submit_button("Generate Meal Plan")
    if submit_button:
        if not ingredients.strip():
            st.error("Please enter at least one ingredient to generate a meal plan.")
        else:
            with st.spinner("Generating your personalized meal plan..."):
                meal_plan = generate_meal_plan(ingredients=ingredients, kcal=kcal, exact_ingredients=exact_ingredients, output_format="text", extra=extra)
                if meal_plan:
                    st.subheader("Your Personalized Meal Plan")
                    st.markdown(meal_plan.replace('\n', '  \n'))  # Preserve line breaks in markdown
                    try: 
                        *plan_body, titles_line = meal_plan.split('\n')
                        plan_titles = titles_line.strip()
                        plan_contents = '\n'.join(plan_body).strip()
                    except ValueError:
                        plan_titles = "Meal Plan Titles Not Found"
                        plan_contents = meal_plan.strip()
                    history_entry = {
                        "titles": plan_titles,
                        "content": plan_contents,
                        "timestamp": datetime.datetime.now(),
                        "inputs":{
                            "ingredients": ingredients,
                            "kcal": kcal,
                            "exact_ingredients": exact_ingredients,
                            "extra": extra
                        }
                    }
                    st.session_state['last_meal_plan'].append(history_entry)
                    st.session_state.history.append(history_entry)

if st.session_state['last_meal_plan']:
    if st.button("Save Meal Plan"):
        saved = save_multiple_records_to_mongo(st.session_state['last_meal_plan'])          
        if saved:
            st.success("Meal plan saved to MongoDB successfully!")
            st.session_state['last_meal_plan'] = []
        else:
            st.error("Failed to save meal plan to MongoDB.")

st.sidebar.title("Meal plan History")
if st.sidebar.button("Clear History"):
    st.session_state['history'] = []
    delete_all_meal_plans()
    st.rerun()


if not st.session_state['history']:
    st.sidebar.info("No meal plans generated yet.")
    meal_plans = fetch_all_meal_plans()
    if meal_plans:
        for plan in meal_plans:
            with st.sidebar.expander(f"**{plan.get("title")}**"):
                st.markdown(plan.get("full_plan").replace('\n', '  \n'))
                st.caption(f"Ingredients: {plan.get("ingredients_input")}")
            
            entry = {
                "titles": plan.get("title", "No Title"),
                "content": plan.get("full_plan", "No Content"),
                "timestamp": plan.get("timestamp"),
                "inputs": {
                    "ingredients": plan.get("ingredients_input"),
                    "kcal": plan.get("calorie_goal"),
                    "exact_ingredients": plan.get("exact_ingredients", False),
                    "extra": plan.get("extra", "")
                }
            }
            st.session_state.history.append(entry)
else:
    for i, entry in enumerate(st.session_state.history):
        with st.sidebar.expander(f"**{entry['titles']}**"):
            st.markdown(entry['content'].replace('\n', '  \n'))
            st.caption(f"Ingredients: {entry['inputs']['ingredients']}")

