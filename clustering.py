import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from umap.umap_ import UMAP  # Correct UMAP import
import json
from bokeh.plotting import figure, show
from bokeh.models import ColumnDataSource, HoverTool
from transformers import AutoTokenizer
from adapters import AutoAdapterModel

# File paths
csv_file = "authors_profiles.csv"
embeddings_file = "embeddings.json"

# Load or initialize CSV
try:
    data = pd.read_csv(csv_file)
except FileNotFoundError:
    data = pd.DataFrame(columns=["name", "oaid", "profile_llm", "profile_llm_human", "classification"])

# Load or initialize embeddings JSON
try:
    with open(embeddings_file, "r") as f:
        embeddings_data = json.load(f)
except FileNotFoundError:
    embeddings_data = {}

# Load SPECTER2 model and tokenizer
def load_specter2_model():
    tokenizer = AutoTokenizer.from_pretrained("allenai/specter2_base")
    model = AutoAdapterModel.from_pretrained("allenai/specter2_base")
    model.load_adapter("allenai/specter2_classification", source="hf", load_as="specter2", set_active=True)
    return tokenizer, model

tokenizer, model = load_specter2_model()

# Generate embedding for a single profile
def generate_embedding(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Text input must be a non-empty string.")
    
    text_batch = [text]
    inputs = tokenizer(
        text_batch, 
        padding=True, 
        truncation=True, 
        return_tensors="pt", 
        return_token_type_ids=False, 
        max_length=512
    )
    output = model(**inputs)
    embedding = output.last_hidden_state[:, 0, :].detach().numpy().flatten()
    return embedding.tolist()

# Update embeddings for new entries
def update_embeddings(data):
    updated = False
    for index, row in data.iterrows():
        oaid = row["oaid"]
        name = row["name"]
        classification = row.get("classification", "Unknown")  # Default if classification is missing
        key = f"{oaid}_{name}"

        # Check if embedding already exists
        if key in embeddings_data:
            continue

        # Use profile_llm_human if available, otherwise fallback to profile_llm
        profile_text = row["profile_llm_human"] if pd.notna(row["profile_llm_human"]) else row["profile_llm"]

        if isinstance(profile_text, str) and profile_text.strip():
            try:
                embedding = generate_embedding(profile_text)
                embeddings_data[key] = {
                    "oaid": oaid,
                    "name": name,
                    "classification": classification,
                    "embedding": embedding,
                }
                updated = True
            except ValueError as e:
                print(f"Skipping row {index}: {e}")
    
    # Save updated embeddings to JSON
    if updated:
        with open(embeddings_file, "w") as f:
            json.dump(embeddings_data, f, indent=4)
    return embeddings_data

# Visualize clusters
def visualize_clusters(data, embeddings_data):
    # Check if the DataFrame is empty
    if data.empty:
        st.error("No data available for visualization.")
        return None

    # Prepare embeddings and metadata
    embeddings = np.array([e["embedding"] for e in embeddings_data.values()])
    names = [e["name"] for e in embeddings_data.values()]
    classifications = [e.get("classification", "Unknown") for e in embeddings_data.values()]

    # Reduce dimensionality with UMAP
    reducer = UMAP(n_neighbors=15, min_dist=0.1, n_components=2, random_state=42)
    reduced_embeddings = reducer.fit_transform(embeddings)

    # Perform clustering
    kmeans = KMeans(n_clusters=3, random_state=42)
    cluster_labels = kmeans.fit_predict(embeddings)

    # Determine the latest entry
    latest_name = data.iloc[-1]["name"] if not data.empty else None

    # Create data source for Bokeh
    source = ColumnDataSource(data={
        "x": reduced_embeddings[:, 0],
        "y": reduced_embeddings[:, 1],
        "name": names,
        "classification": classifications,
        "is_latest": [name == latest_name for name in names],
        "cluster": cluster_labels
    })

    # Create the Bokeh plot
    plot = figure(
        title="Clusters of Profiles (UMAP + KMeans)",
        x_axis_label="UMAP 1",
        y_axis_label="UMAP 2",
        tools="pan,zoom_in,zoom_out,reset,save",
        height=500,
        width=800,
    )
    plot.scatter(
        x="x", y="y", source=source, size=10, color="is_latest", legend_field="classification", alpha=0.8
    )

    hover = HoverTool()
    hover.tooltips = [("Name", "@name"), ("Classification", "@classification"), ("Cluster", "@cluster")]
    plot.add_tools(hover)

    return plot