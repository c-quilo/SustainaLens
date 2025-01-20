from itertools import chain
import json
import os
import pandas as pd
from pyalex import Works

def fetch_papers_and_update_json(input_csv, output_json):
    """
    Fetch papers for authors in the input CSV and update the JSON file.

    Args:
        input_csv (str): Path to the input CSV file with 'oaid' and 'name' columns.
        output_json (str): Path to the output JSON file where data will be updated.

    Returns:
        dict: The author data and the result count.
    """
    # Check if the JSON file exists and is valid
    if not os.path.exists(output_json) or os.path.getsize(output_json) == 0:
        print(f"Initializing JSON file at {output_json}")
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump([], f)

    try:
        # Load the existing JSON data
        with open(output_json, 'r', encoding='utf-8') as f:
            output_data = json.load(f)
    except json.JSONDecodeError:
        print(f"Error reading JSON file at {output_json}. Reinitializing.")
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump([], f)
        output_data = []

    try:
        # Load the CSV with authors
        df = pd.read_csv(input_csv)
    except FileNotFoundError:
        raise FileNotFoundError(f"The file {input_csv} does not exist. Please ensure it contains 'oaid' and 'name' columns.")

    # Ensure required columns exist in the DataFrame
    if 'oaid' not in df.columns or 'name' not in df.columns:
        raise ValueError(f"The file {input_csv} must contain 'oaid' and 'name' columns.")

    # Get the latest entry from the CSV
    latest_entry = df.iloc[-1]
    oaid_url = latest_entry['oaid']
    author_name = latest_entry['name']
    oaid = oaid_url

    print(f"Fetching papers for the latest author: {author_name} (OAID: {oaid})")

    # Define the query for the specific author
    query = Works().filter(
        type='article|preprint|book-chapter|dissertation'
    ).filter(
        authorships={"author": {'id': oaid_url}}
    ).filter(
        publication_year='>2010'
    ).filter(
        has_abstract='True'
    )

    result_count = query.count()
    print(f"Number of filtered results for OAID {oaid}: {result_count}")

    # Collect papers if results exist
    papers = []
    if result_count > 0:
        for item in chain(*query.paginate(per_page=200, n_max=None)):
            paper_data = {
                'id': item['id'],
                'doi': item['doi'],
                'topic_id': item['primary_topic']['id'] if item['primary_topic'] else None,
                'publication_year': item['publication_year'],
                'cited_by_count': item['cited_by_count'],
                'title': item['title'],
                'abstract': item['abstract'],
                'citations_per_year': round(
                    float(item['cited_by_count']) /
                    max((2026 - float(item['publication_year'])), 1), 2
                ),
                'is_corresponding_author': oaid_url in item['corresponding_author_ids'],
            }
            papers.append(paper_data)

    # Load existing JSON or initialize empty structure
    try:
        with open(output_json, 'r', encoding='utf-8') as f:
            output_data = json.load(f)
    except FileNotFoundError:
        output_data = []

    # Check if the author already exists in the JSON
    author_exists = any(author['author_id'] == oaid for author in output_data)

    if author_exists:
        print(f"Author {author_name} (OAID: {oaid}) already exists in the JSON.")
    else:
        # Add the latest author's data to the JSON structure
        output_data.append({
            'author_id': oaid,
            'name': author_name,
            'papers': papers
        })

        # Save the updated JSON file
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=4, ensure_ascii=False)

        print(f"Updated JSON with {author_name} (OAID: {oaid}).")

    return {'author_id': oaid, 'name': author_name, 'papers': papers}, result_count