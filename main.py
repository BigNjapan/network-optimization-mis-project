from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd


REQUIRED_COLUMNS = {"source", "target", "capacity_mbps", "description"}
MINIMUM_NODE_COUNT = 6
MINIMUM_EDGE_COUNT = 8


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Solve a data center maximum flow problem from a CSV edge list."
    )
    parser.add_argument("--data", default="data_edges.csv", help="Path to the CSV edge list.")
    parser.add_argument(
        "--source",
        default="Internet_Gateway",
        help="Source node where network traffic starts.",
    )
    parser.add_argument(
        "--sink",
        default="Analytics_Dashboard",
        help="Sink node where network traffic is delivered.",
    )
    parser.add_argument(
        "--plot",
        default="outputs/data_center_flow.png",
        help="Path where the network plot will be saved.",
    )
    return parser.parse_args()


def load_edges(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")

    edges = pd.read_csv(path)
    missing_columns = REQUIRED_COLUMNS.difference(edges.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"CSV is missing required column(s): {missing}")

    edges["capacity_mbps"] = pd.to_numeric(edges["capacity_mbps"], errors="coerce")
    if edges["capacity_mbps"].isna().any():
        raise ValueError("All capacity_mbps values must be numeric.")
    if (edges["capacity_mbps"] <= 0).any():
        raise ValueError("All capacity_mbps values must be positive.")

    node_count = pd.unique(edges[["source", "target"]].values.ravel()).size
    if node_count < MINIMUM_NODE_COUNT:
        raise ValueError(f"The network must include at least {MINIMUM_NODE_COUNT} nodes.")
    if len(edges) < MINIMUM_EDGE_COUNT:
        raise ValueError(f"The network must include at least {MINIMUM_EDGE_COUNT} edges.")

    return edges


def build_graph(edges: pd.DataFrame) -> nx.DiGraph:
    graph = nx.DiGraph()
    for edge in edges.itertuples(index=False):
        graph.add_edge(
            edge.source,
            edge.target,
            capacity=float(edge.capacity_mbps),
            description=edge.description,
        )
    return graph


def validate_terminals(graph: nx.DiGraph, source: str, sink: str) -> None:
    if source not in graph:
        raise ValueError(f"Source node does not exist in the network: {source}")
    if sink not in graph:
        raise ValueError(f"Sink node does not exist in the network: {sink}")
    if source == sink:
        raise ValueError("Source and sink must be different nodes.")


def solve_max_flow(graph: nx.DiGraph, source: str, sink: str) -> tuple[float, dict[str, dict[str, float]]]:
    flow_value, flow_dict = nx.maximum_flow(graph, source, sink, capacity="capacity")
    return float(flow_value), flow_dict


def format_number(value: float) -> str:
    return str(int(value)) if value.is_integer() else f"{value:.2f}"


def print_results(graph: nx.DiGraph, source: str, sink: str, flow_value: float, flow_dict: dict[str, dict[str, float]]) -> None:
    print("Data Center Maximum Flow Analysis")
    print("=" * 38)
    print(f"Source: {source}")
    print(f"Sink: {sink}")
    print(f"Maximum flow: {format_number(flow_value)} Mbps")
    print()

    print("Edge flows:")
    saturated_edges: list[str] = []
    for start, end, data in graph.edges(data=True):
        capacity = float(data["capacity"])
        flow = float(flow_dict[start][end])
        print(f"- {start} -> {end}: {format_number(flow)} / {format_number(capacity)} Mbps")
        if flow == capacity:
            saturated_edges.append(f"{start} -> {end}")

    print()
    print("Saturated edges:")
    if saturated_edges:
        for edge in saturated_edges:
            print(f"- {edge}")
    else:
        print("- None")


def save_flow_plot(graph: nx.DiGraph, flow_dict: dict[str, dict[str, float]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    positions = nx.spring_layout(graph, seed=7, k=1.1)
    edge_colors = []
    edge_widths = []
    edge_labels = {}

    for start, end, data in graph.edges(data=True):
        capacity = float(data["capacity"])
        flow = float(flow_dict[start][end])
        edge_colors.append("#c94f4f" if flow == capacity else "#4f6f9f")
        edge_widths.append(1.5 + (3.0 * flow / capacity if capacity else 0))
        edge_labels[(start, end)] = f"{format_number(flow)}/{format_number(capacity)} Mbps"

    plt.figure(figsize=(13, 8))
    nx.draw_networkx_nodes(graph, positions, node_size=2600, node_color="#d9ead3", edgecolors="#2f5233")
    nx.draw_networkx_labels(graph, positions, font_size=9, font_weight="bold")
    nx.draw_networkx_edges(
        graph,
        positions,
        arrows=True,
        arrowsize=18,
        edge_color=edge_colors,
        width=edge_widths,
        connectionstyle="arc3,rad=0.08",
    )
    nx.draw_networkx_edge_labels(graph, positions, edge_labels=edge_labels, font_size=8, label_pos=0.55)

    plt.title("Data Center Maximum Flow Network", fontsize=14, fontweight="bold")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()


def main() -> None:
    args = parse_args()
    data_path = Path(args.data)
    plot_path = Path(args.plot)

    edges = load_edges(data_path)
    graph = build_graph(edges)
    validate_terminals(graph, args.source, args.sink)

    flow_value, flow_dict = solve_max_flow(graph, args.source, args.sink)
    print_results(graph, args.source, args.sink, flow_value, flow_dict)
    save_flow_plot(graph, flow_dict, plot_path)
    print()
    print(f"Plot saved to: {plot_path}")


if __name__ == "__main__":
    main()
