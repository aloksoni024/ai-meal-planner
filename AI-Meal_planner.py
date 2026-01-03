import streamlit as st
from openai import AzureOpenAI
import os

st.set_page_config(page_title="AI Meal Planner", page_icon="🍽️", layout="centered")


try: 
    print("Loading OpenAI API key from Streamlit secrets...")
    client = AzureOpenAI(api_key=os.getenv("AZURE_OPENAI_API_KEY2"), api_version="2024-12-01-preview", azure_endpoint="https://autodub-whispurr-temp.openai.azure.com")
except KeyError:
    st.error("OpenAI API key not found. Please set it in Streamlit secrets.")
    st.stop()

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
                    # st.text_area("Meal Plan:", meal_plan, height=400)
                    # titles_line = meal_plan.strip().split('\n')[-1]
                    # st.success(f"Meal Titles: {titles_line}")
