import streamlit as st
import pandas as pd
from pyalex import Works, Authors
import os
import time
import json
from nameSearch import findNameAndPopulate
from fetchPapers import fetch_papers_and_update_json
from profileWriter import generate_profile_for_latest_entry, regenerate_profile
# from clustering import update_embeddings, visualize_clusters

# Load or Initialize CSV
filename = "authors_profiles.csv"
try:
    data = pd.read_csv(filename)
except FileNotFoundError:
    data = pd.DataFrame(columns=["name", "oaid", "institution", "profile_llm", "human_input", "profile_llm_human", "classification", "input"])

# Set the Streamlit theme to Light
st.set_page_config(page_title="Profile Builder", layout="wide", initial_sidebar_state="expanded")

# Add tabs
tab_profile, tab_graph = st.tabs(["Profile Builder", "Graph"])

with tab_profile:
    sidebar_logo_path = "logo_sidebar/logo.png"
    # Display logo at the top of the sidebar
    if os.path.exists(sidebar_logo_path):
        st.sidebar.image(sidebar_logo_path, use_container_width=True)

    st.header("LLM-based profile builder")
    # Sidebar Inputs
    st.sidebar.header("Inputs")

    # Toggle button to choose input method
    input_mode = st.sidebar.radio("Select Input Method", ("Name", "OpenAlex ID"))

    if input_mode == "Name":
        # Input Author's Name
        author_name = st.sidebar.text_input("Enter Author Name")
        institution = 'Imperial College London'
    else:
        # Input OpenAlex ID and optional name
        openalex_id = st.sidebar.text_input("Enter OpenAlex ID")
        author_name = st.sidebar.text_input("Enter Author Name")
        institution = st.sidebar.text_input("Institution")

    # Button to initiate the process
    search_button = st.sidebar.button("Search and generate profile")

    if search_button:
        if input_mode == "Name" and author_name:
            # Normalize the case of the input name
            author_name_normalized = author_name.strip().lower()

            # Access OpenAlex to get information for the author
            oaid, name = findNameAndPopulate(author_name)

            # Normalize the 'name' column
            data['name_normalised'] = data['name'].astype(str).str.lower().str.strip()
            
            # Check for duplicates using the normalized name
            if author_name_normalized in data['name_normalised'].values:
                st.warning(f"{name.title()} is already in the database.")
            else:
                # Add the author to the DataFrame
                new_row = {"oaid": oaid, "name": name, "institution": institution}
                data = pd.concat([data, pd.DataFrame([new_row])], ignore_index=True)

                # Drop the temporary 'name_normalized' column
                data = data.drop(columns=['name_normalised'])

                # Save the updated CSV
                data.to_csv(filename, index=False)

                # Fetch papers for the latest author and update the JSON
                with st.spinner(text='Fetching papers'):
                    author_data, result_count = fetch_papers_and_update_json(
                        filename, output_json='authors_papers.json'
                    )
                
                    # Display a success message with the result count
                    if result_count > 0:
                        st.success(f"Added {name.title()} (OpenAlex ID: {oaid}) to the database. Found {result_count} papers.")
                    else:
                        st.warning(f"Added {name.title()} (OpenAlex ID: {oaid}) to the database, but no papers were found.")

                with st.spinner(text='Generating profile'):
                    generate_profile_for_latest_entry(
                        json_file='authors_papers.json',
                        output_csv='authors_profiles.csv'
                    )
                    st.success(f"Profile for {name.title()} has been generated and saved.")

        elif input_mode == "OpenAlex ID" and openalex_id:
            # Use the OpenAlex ID directly to fetch papers
            oaid = openalex_id.strip()
            name = author_name.strip() if author_name else "Unknown Author"

            # Add the author to the DataFrame
            new_row = {"oaid": oaid, "name": name, "institution": institution}
            data = pd.concat([data, pd.DataFrame([new_row])], ignore_index=True)

            # Save the updated CSV
            data.to_csv(filename, index=False)

            # Fetch papers for the given OpenAlex ID and update the JSON
            with st.spinner(text='Fetching papers'):
                author_data, result_count = fetch_papers_and_update_json(
                    filename, output_json='authors_papers.json'
                )
                
                # Display a success message with the result count
                if result_count > 0:
                    st.success(f"Added {name.title()} (OpenAlex ID: {oaid}) to the database. Found {result_count} papers.")
                else:
                    st.warning(f"Added {name.title()} (OpenAlex ID: {oaid}) to the database, but no papers were found.")

            with st.spinner(text='Generating profile'):
                generate_profile_for_latest_entry(
                    json_file='authors_papers.json',
                    output_csv='authors_profiles.csv'
                )
                st.success(f"Profile for {name.title()} has been generated and saved.")

        else:
            st.error("Please provide the required input to proceed.")
        
        # Load the profiles CSV to fetch the latest profile
        profiles_df = pd.read_csv('authors_profiles.csv')
        profile_row = profiles_df.loc[profiles_df['oaid'] == oaid]

        if not profile_row.empty:
            # Extract and display the profile
            latest_profile = profile_row.iloc[0]['profile_llm']
            st.subheader(f"Generated Profile for {name.title()}")
            st.write(latest_profile)
        else:
            st.error(f"No profile found for {name.title()} (OAID: {oaid}). Please check the data.")

    # Access OpenAlex to get information for the author
    oaid, name = findNameAndPopulate(author_name)

    # Load the profiles CSV to fetch the latest profile

    profiles_df = pd.read_csv('authors_profiles.csv')
    profile_row = profiles_df.loc[profiles_df['oaid'] == oaid]

    if not profile_row.empty:
        # Extract and display the profile
        latest_profile = profile_row.iloc[0]['profile_llm']
    else:
        st.error(f"No profile found for {name.title()} (OAID: {oaid}). Please check the data.")

    # Initialize session state for feedback
    if "feedback" not in st.session_state:
        st.session_state.feedback = ""
    if "no_confirmed" not in st.session_state:
        st.session_state.no_confirmed = False

    # Feedback Section
    st.sidebar.subheader("Does it need improvement?")
    feedback = st.sidebar.radio(
        "Choose one:",
        options=["Yes, I want to add input", "No"],
        index=0 if st.session_state.feedback == "" else ["Yes, I want to add input", "No"].index(st.session_state.feedback),
        key="feedback_radio"
    )
    st.session_state.feedback = feedback

    if feedback == "Yes, I want to add input":
        # Text area for human input
        user_input = st.sidebar.text_area(
            "Add your input (max 200 characters):",
            max_chars=200,
            key="human_input"
        )

        # Button to submit input and regenerate profile
        if st.sidebar.button("Submit Input"):
            if user_input.strip():
                print(f"User Input: {user_input}")  # Debug print

                # Save the human input in the CSV
                profiles_df.loc[profiles_df['oaid'] == oaid, 'human_input'] = user_input
                profiles_df.loc[profiles_df['oaid'] == oaid, 'input'] = "Yes"
                profiles_df.to_csv('authors_profiles.csv', index=False)
                print("Saved user input to CSV.")  # Debug print

                # Regenerate the profile with the new input
                with st.spinner("Regenerating profile..."):
                    new_profile = regenerate_profile(latest_profile, user_input)
                    print(f"New Profile: {new_profile}")  # Debug print
                    profiles_df.loc[profiles_df['oaid'] == oaid, 'profile_llm_human'] = new_profile
                    profiles_df.to_csv('authors_profiles.csv', index=False)

                st.sidebar.success("The profile has been updated with your input!")

                # Display profiles for comparison
                st.subheader(f"Updated Profile for {name.title()}")
                st.write("### Original Profile")
                st.write(latest_profile)
                st.write("### Updated Profile")
                st.write(new_profile)
            else:
                st.sidebar.error("Please provide input before submitting.")

    if feedback == "No":
        # Check session state to persist the confirmation
        if not st.session_state.no_confirmed:
            print("Feedback: No")  # Debug print
            profiles_df.loc[profiles_df['oaid'] == oaid, 'input'] = "No"
            profiles_df.to_csv('authors_profiles.csv', index=False)
            print("Saved 'No' feedback to CSV.")  # Debug print

            st.sidebar.success("Thank you for your feedback!")
            st.session_state.no_confirmed = True
        else:
            st.sidebar.success("You have already confirmed 'No'.")

with tab_graph:
    st.header("Cluster Visualisation")

    # Load CSV and embeddings data
    try:
        data = pd.read_csv('authors_profiles.csv')
    except FileNotFoundError:
        st.error("No profiles found. Please add profiles first.")
        st.stop()
