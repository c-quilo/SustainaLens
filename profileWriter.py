import os
import json
import pandas as pd
import time
from openai import OpenAI

# Load OpenAI API key from environment variables
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# File paths
json_file = 'authors_papers.json'
output_csv = 'authors_profiles.csv'

# Pre-prompt for OpenAI
pre_prompt = '''
You are writing a scientific outreach profile for researchers and scientists. This needs to be engaging and not too specific.
Classify the researcher within 2 or 3 climate tech challenge spaces (defined by you). Be specific.
Only provide truthful insights based on the provided information. Use British English.
'''

def query_openai_profile(titles_and_abstracts, author_name):
    """
    Query OpenAI API to generate a profile for a researcher.
    """
    prompt = f"""
    The researcher's name is {author_name}.
    Here are selected titles and abstracts for this researcher:
    {titles_and_abstracts}

    Based on this information, write a very brief 50-100 words profile for the researcher starting with
    variations of '{author_name} specialises in' or '{author_name}'s work focuses ...', use other ways to say this as well.
    The profile needs to be written in layman terms, but still add keywords or 
    technical words if you need to. Write it like a holistic view of what the researcher does. 
    And classify their work within 2 or 3 best-fit climate tech challenge spaces specified by you, 
    in this format: Relevant climate challenges: X, Y, Z
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": pre_prompt},
            {"role": "user", "content": prompt}
        ],
        max_tokens=500,
        temperature=0.5
    )
    content = response.choices[0].message.content.strip()

    # Extract classification challenges
    challenges_start = content.find("Relevant climate challenges: ")
    if challenges_start != -1:
        challenges_text = content[challenges_start + len("Relevant climate challenges: "):].strip()
        challenges = [challenge.strip() for challenge in challenges_text.split(",")]
    else:
        challenges = []

    return content, challenges

def generate_profile_for_latest_entry(json_file, output_csv):
    """
    Generate a profile for the latest entry in the CSV file and match it with the JSON data.
    """
    # Load papers from the JSON file
    with open(json_file, 'r', encoding='utf-8') as f:
        authors_data = json.load(f)

    # Check if the JSON is empty
    if not authors_data:
        print("No authors found in the JSON file.")
        return

    # Load or initialize the output CSV
    if os.path.exists(output_csv):
        profiles_df = pd.read_csv(output_csv)
    else:
        profiles_df = pd.DataFrame(columns=['oaid', 'name', 'profile_llm', 'classification'])

    # Get the latest entry in the CSV
    if profiles_df.empty:
        print("The profiles CSV is empty. No latest entry to process.")
        return

    latest_entry = profiles_df.iloc[-1]  # Retrieve the last row
    oaid_normalized = latest_entry['oaid'].lower().strip()
    name_normalized = latest_entry['name'].lower().strip()

    # Match the latest entry with the JSON data
    matched_author = next(
        (author for author in authors_data
         if author['oaid'].lower().strip() == oaid_normalized and
         author['name'].lower().strip() == name_normalized),
        None
    )

    if not matched_author:
        print(f"No matching author found in the JSON file for {latest_entry['name']} (OAID: {latest_entry['oaid']}).")
        return

    # Extract matched author's data
    papers = matched_author.get('papers', [])
    selected_papers = papers[:10]  # Top 10 papers
    titles_and_abstracts = "\n".join(
        f"Title: {paper['title']}\nAbstract: {paper['abstract']}"
        for paper in selected_papers if paper['abstract']
    )

    # Generate the profile and challenges using OpenAI
    if titles_and_abstracts.strip():
        profile_text, classification = query_openai_profile(titles_and_abstracts, latest_entry['name'])
    else:
        profile_text = f"No abstracts available to generate a detailed profile for {latest_entry['name']}."
        classification = []

    classification_str = json.dumps(classification)

    # Check if the profile already exists
    existing_profile_index = profiles_df[
        (profiles_df['oaid'].str.lower().str.strip() == oaid_normalized) &
        (profiles_df['name'].str.lower().str.strip() == name_normalized)
    ].index

    if not existing_profile_index.empty:
        existing_profile_index = existing_profile_index[0]
        profiles_df.at[existing_profile_index, 'profile_llm'] = profile_text
        profiles_df.at[existing_profile_index, 'classification'] = classification_str
    else:
        # Add a new row
        new_row = pd.DataFrame([{
            'oaid': matched_author['oaid'],
            'name': matched_author['name'],
            'profile_llm': profile_text,
            'classification': classification_str
        }])
        profiles_df = pd.concat([profiles_df, new_row], ignore_index=True)

    # Save the updated CSV
    profiles_df.to_csv(output_csv, index=False)

    print(f"Profile for {latest_entry['name']} (OAID: {latest_entry['oaid']}) has been saved to {output_csv}")

def regenerate_profile(existing_profile, user_input):
    """
    Regenerate a profile based on the existing profile and user input.
    
    Args:
        existing_profile (str): The original profile text.
        user_input (str): Additional input from the user.

    Returns:
        str: The updated profile generated by the LLM.
    """
    prompt = f"""
    Here is the original profile:
    {existing_profile}

    The user has provided additional input:
    {user_input}

    Update the profile to include the user's input while maintaining the same professional tone.
    Ensure the profile remains concise and within 100 words. 
    Re-write the Relevant climate challenges in the format: X, Y, Z
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": pre_prompt},
            {"role": "user", "content": prompt}
        ],
        max_tokens=500,
        temperature=0.5
    )
    content = response.choices[0].message.content.strip()
    return content
