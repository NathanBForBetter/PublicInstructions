import pandas as pd
import openai
import time

key_1 = '[YOUR OPEN AI KEY]'
file_path = '/Users/nathanbeddome/Downloads'
input_csv_file_name = 'restaurant-feedback - reviews.csv'
output_csv_file_name = 'restaurant-feedback-ai-categories.csv'

def gpt_call(prompt, key):
    openai.api_key = key
    completion = openai.chat.completions.create(
        model='gpt-4o',
        messages=[
            {
                'role': 'user',
                'content': f'{prompt}',
            },
        ],
    )
    response = completion.choices[0].message.content
    time.sleep(1)
    return response
## up to 5 Comma separated 1-2 word emotion words straight up for feedback and ratings
## Great, Good, Neutral, Bad, Terrible for feedback and ratings
## Categorize restuarant with 1-2 words and use prev examples. 

output_df_headers = [
  'restaurant_feedback', 'restaurant_name', 'restaurant_rating',
  'ai_category_type', 'ai_category']
starter_output_df = pd.DataFrame(columns=output_df_headers)
starter_output_df.to_csv(f'{file_path}/{output_csv_file_name}', index=False)

input_file = open(f'{file_path}/{input_csv_file_name}')
input_df = pd.read_csv(input_file).fillna('')

prev_restuarant_categories = ['burger fast food']

for index, row in input_df.iterrows():
  restaurant_feedback = row['restaurant_feedback']
  restaurant_name = row['restaurant_name']
  restaurant_rating = row['restaurant_rating_out_of_5']

  ai_category_type = 'feedback_emotion'
  feedback_emotion_prompt = f'''
    What are 5 comma separated 1-2 words that describe the emotion
    of this restaurant feedback {restaurant_feedback} combined with 
    their rating of {restaurant_rating} for the restaurant. Just pass the comma separated words.'''
  feedback_emotion_response = gpt_call(feedback_emotion_prompt, key_1)
  feedback_emotion_responses = feedback_emotion_response.split(feedback_emotion_response, ',')
  for feedback_emotion in feedback_emotion_responses:
    output_df = pd.DataFrame([[restaurant_feedback, restaurant_name, restaurant_rating, ai_category_type, feedback_emotion]], columns=output_df_headers)
    output_df.to_csv(f'{file_path}/{output_csv_file_name}', mode='a', header=False, index=False)
  
  ai_category_type = 'feedback_scale'
  feedback_scale_prompt = f'''
    Choose one category out of these 5 for [Great, Good, Neutral, Bad, Terrible]
    this restaurant feedback {restaurant_feedback} combined with 
    their rating of {restaurant_rating} for the restaurant. Just pass the one category.'''
  feedback_scale_response = gpt_call(feedback_scale_prompt, key_1)
  output_df = pd.DataFrame([[restaurant_feedback, restaurant_name, restaurant_rating, ai_category_type, feedback_scale_response]], columns=output_df_headers)
  output_df.to_csv(f'{file_path}/{output_csv_file_name}', mode='a', header=False, index=False)
  
  ai_category_type = 'restaurant_category'
  prev_restuarant_categories_string = ','.join(prev_restuarant_categories)
  restaurant_category_prompt = f'''
    Choose one category for this restaurant {restaurant_name} including one of these categories ({prev_restuarant_categories_string})
    only if its relevant. Just pass the one category.'''
  restaurant_category_response = gpt_call(restaurant_category_prompt, key_1)
  output_df = pd.DataFrame([[restaurant_feedback, restaurant_name, restaurant_rating, ai_category_type, restaurant_category_response]], columns=output_df_headers)
  output_df.to_csv(f'{file_path}/{output_csv_file_name}', mode='a', header=False, index=False)
print('yay its done!')