"""LangGraph pipeline: ingestion -> embedding/clustering -> momentum -> cross_source -> categorize -> synthesis."""
from langgraph.graph import StateGraph, END
from app.agents.state import TrendPipelineState
from app.agents.ingestion import run_ingestion
from app.agents.embedding_clustering import run_embedding_clustering
from app.agents.momentum import run_momentum
from app.agents.cross_source import run_cross_source_validation
from app.agents.categorize import run_categorize
from app.agents.synthesis import run_synthesis


def create_trend_graph() -> StateGraph:
    """Build the trend pipeline graph."""
    graph = StateGraph(TrendPipelineState)

    graph.add_node("ingestion", run_ingestion)
    graph.add_node("embedding_clustering", run_embedding_clustering)
    graph.add_node("momentum", run_momentum)
    graph.add_node("cross_source", run_cross_source_validation)
    graph.add_node("categorize", run_categorize)
    graph.add_node("synthesis", run_synthesis)

    graph.set_entry_point("ingestion")
    graph.add_edge("ingestion", "embedding_clustering")
    graph.add_edge("embedding_clustering", "momentum")
    graph.add_edge("momentum", "cross_source")
    graph.add_edge("cross_source", "categorize")
    graph.add_edge("categorize", "synthesis")
    graph.add_edge("synthesis", END)

    return graph.compile()


def run_pipeline() -> dict:
    """Execute the full pipeline and return final state."""
    compiled = create_trend_graph()
    initial: TrendPipelineState = {}
    result = compiled.invoke(initial)
    return result
