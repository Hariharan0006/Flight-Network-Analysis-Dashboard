from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import os

# --------------------------------------------------
# App Configuration
# --------------------------------------------------

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
STATIC_FOLDER = "static"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STATIC_FOLDER, exist_ok=True)

data = None


# --------------------------------------------------
# Utility Functions
# --------------------------------------------------

def clean_dataframe(df):
    """Clean and prepare dataframe"""
    df.columns = df.columns.str.strip()
    df = df.dropna(subset=["source airport", "destination airport"])
    df = df[df["source airport"] != df["destination airport"]]
    return df


def build_graph(df):
    """Build directed graph"""
    G = nx.DiGraph()
    G.add_edges_from(zip(df["source airport"], df["destination airport"]))
    return G


def compute_metrics(G):
    """Compute fast degree-based metrics"""
    in_degree = dict(G.in_degree())
    out_degree = dict(G.out_degree())

    result_df = pd.DataFrame({
        "Airport": list(G.nodes()),
        "In_Degree": [in_degree[n] for n in G.nodes()],
        "Out_Degree": [out_degree[n] for n in G.nodes()]
    })

    result_df = result_df.sort_values(by="Out_Degree", ascending=False)
    return result_df


def generate_visualization(G, result_df):
    """Clean directed visualization with clear arrows"""

    # Take Top 15 airports only (less clutter)
    top_airports = result_df.head(15)["Airport"].tolist()
    G_small = G.subgraph(top_airports)

    plt.figure(figsize=(10, 8))

    # Better spacing layout
    pos = nx.spring_layout(G_small, k=0.8, seed=42)

    # Smaller node size
    node_sizes = [
        result_df[result_df["Airport"] == n]["Out_Degree"].values[0] * 20
        for n in G_small.nodes()
    ]

    # Draw Nodes
    nx.draw_networkx_nodes(
        G_small,
        pos,
        node_size=node_sizes,
        node_color="#2E86C1",
        alpha=0.9
    )

    # Draw Edges with clear arrows
    nx.draw_networkx_edges(
        G_small,
        pos,
        arrowstyle='-|>',
        arrowsize=15,
        edge_color="#555555",
        width=1.2,
        connectionstyle='arc3,rad=0.1'
    )

    # Draw Labels
    nx.draw_networkx_labels(
        G_small,
        pos,
        font_size=9,
        font_weight="bold"
    )

    plt.title("Top 15 Airports - Directed Route Network", fontsize=13)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig("static/graph.png", dpi=300)
    plt.close()


# --------------------------------------------------
# Routes
# --------------------------------------------------

@app.route('/')
def index():
    return render_template("index.html")


@app.route('/upload', methods=["POST"])
def upload():
    global data

    file = request.files.get("file")

    if not file or file.filename == "":
        return "No file selected"

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(filepath)

    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        return f"Error reading file: {e}"

    df.columns = df.columns.str.strip()

    required_cols = {"source airport", "destination airport"}

    if not required_cols.issubset(set(df.columns)):
        return f"Required columns not found. Columns available: {df.columns}"

    data = df

    return render_template(
        "table.html",
        tables=[df.head(20).to_html(classes='data')],
        titles=df.columns.values
    )


@app.route('/analyze')
def analyze():
    global data

    if data is None:
        return redirect(url_for('index'))

    df = clean_dataframe(data)

    G = build_graph(df)

    result_df = compute_metrics(G)

    generate_visualization(G, result_df)

    return render_template(
        "results.html",
        tables=[result_df.head(20).to_html(classes='data')],
        titles=result_df.columns.values
    )


# --------------------------------------------------

if __name__ == '__main__':
    app.run(debug=True)
