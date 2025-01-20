import pandas as pd
from pyalex import Authors

# Load or initialize the CSV file
filename = 'authors_profiles.csv'
try:
    # Load existing CSV (assuming it already has 'name' and 'oaid' columns)
    df = pd.read_csv(filename)
except FileNotFoundError:
    # Initialize an empty DataFrame if the file doesn't exist
    df = pd.DataFrame(columns=['name', 'oaid'])

def findNameAndPopulate(name):
    global df  # Access the global DataFrame

    # Ensure that the required columns exist
    if 'name' not in df.columns or 'oaid' not in df.columns:
        raise ValueError(f"The file {filename} must contain 'name' and 'oaid' columns.")

    print(f"Searching for OpenAlex ID for author: {name}")

    # Check if the name is already in the DataFrame
    if name in df['name'].values:
        oaid = df.loc[df['name'] == name, 'oaid'].values[0]
        print(f"{name} already exists in the CSV with OpenAlex ID: {oaid}")
        return oaid, name  # Return the existing name and ID

    # Add the new name to the DataFrame with an empty 'oaid'
    new_row = {'name': name, 'oaid': None}
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    # Save the updated DataFrame immediately to avoid losing the new row
    df.to_csv(filename, index=False)

    # Search for the author in OpenAlex
    author_search = Authors().search_filter(
        display_name=name
    ).filter(
        affiliations={"institution": {'id': "https://openalex.org/I47508984"}}
    )

    # Try to retrieve the OpenAlex ID, or set it to None if not found
    try:
        author_data = author_search.get()[0]['id']
    except IndexError:
        author_data = None  # No match found

    # Update the 'oaid' for the row with the matching name
    df.loc[df['name'] == name, 'oaid'] = author_data

    # Save the updated DataFrame to the CSV
    df.to_csv(filename, index=False)

    print(f"Updated DataFrame:\n{df}")
    print(f"Author ID: {author_data}")
    print(f"Name: {name}")

    return author_data, name