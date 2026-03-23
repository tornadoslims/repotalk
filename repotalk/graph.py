"""Knowledge graph using NetworkX — build, query, export, Mermaid diagrams."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import networkx as nx

from repotalk.models import EdgeType, FileAnalysis, GraphEdge, GraphNode

logger = logging.getLogger(__name__)


class KnowledgeGraph:
    """Directed knowledge graph of codebase entities and relationships."""

    def __init__(self) -> None:
        self.graph = nx.DiGraph()
        self._file_analyses: dict[str, FileAnalysis] = {}

    def build_from_analyses(self, analyses: list[FileAnalysis]) -> None:
        """Build the complete graph from a list of file analyses."""
        for analysis in analyses:
            self._file_analyses[analysis.relative_path] = analysis
            self._add_file_node(analysis)
            self._add_directory_nodes(analysis)
            self._add_function_nodes(analysis)
            self._add_class_nodes(analysis)

        # Second pass: resolve edges
        for analysis in analyses:
            self._add_import_edges(analysis)
            self._add_call_edges(analysis)
            self._add_inheritance_edges(analysis)
            self._add_decorator_edges(analysis)

        logger.info(
            "Graph built: %d nodes, %d edges",
            self.graph.number_of_nodes(),
            self.graph.number_of_edges(),
        )

    def _add_file_node(self, analysis: FileAnalysis) -> None:
        self.graph.add_node(
            analysis.relative_path,
            type="file",
            name=Path(analysis.relative_path).name,
            file_path=analysis.relative_path,
            module_name=analysis.module_name,
            line_count=analysis.line_count,
            docstring=analysis.module_docstring or "",
        )

    def _add_directory_nodes(self, analysis: FileAnalysis) -> None:
        rel = Path(analysis.relative_path)
        for parent in rel.parents:
            if str(parent) == ".":
                continue
            dir_id = str(parent)
            if not self.graph.has_node(dir_id):
                self.graph.add_node(
                    dir_id,
                    type="directory",
                    name=parent.name,
                    file_path=dir_id,
                )
            self.graph.add_edge(
                dir_id,
                analysis.relative_path,
                edge_type=EdgeType.CONTAINS.value,
            )

    def _add_function_nodes(self, analysis: FileAnalysis) -> None:
        for func in analysis.functions:
            node_id = func.qualified_name or f"{analysis.module_name}.{func.name}"
            self.graph.add_node(
                node_id,
                type="function",
                name=func.name,
                file_path=analysis.relative_path,
                is_async=func.is_async,
                line_start=func.line_start,
                complexity=func.complexity,
            )
            self.graph.add_edge(
                analysis.relative_path,
                node_id,
                edge_type=EdgeType.DEFINES.value,
            )

    def _add_class_nodes(self, analysis: FileAnalysis) -> None:
        for cls in analysis.classes:
            node_id = cls.qualified_name or f"{analysis.module_name}.{cls.name}"
            self.graph.add_node(
                node_id,
                type="class",
                name=cls.name,
                file_path=analysis.relative_path,
                line_start=cls.line_start,
                bases=cls.bases,
            )
            self.graph.add_edge(
                analysis.relative_path,
                node_id,
                edge_type=EdgeType.DEFINES.value,
            )
            # Method nodes
            for method in cls.methods:
                method_id = f"{node_id}.{method.name}"
                self.graph.add_node(
                    method_id,
                    type="method",
                    name=method.name,
                    file_path=analysis.relative_path,
                    is_async=method.is_async,
                    line_start=method.line_start,
                )
                self.graph.add_edge(
                    node_id,
                    method_id,
                    edge_type=EdgeType.DEFINES.value,
                )

    def _add_import_edges(self, analysis: FileAnalysis) -> None:
        for imp in analysis.imports:
            # Try to find target file node
            target = self._resolve_import(imp.module, analysis)
            if target and self.graph.has_node(target):
                self.graph.add_edge(
                    analysis.relative_path,
                    target,
                    edge_type=EdgeType.IMPORTS.value,
                    names=imp.names,
                )

    def _add_call_edges(self, analysis: FileAnalysis) -> None:
        all_functions = {n: d for n, d in self.graph.nodes(data=True) if d.get("type") in ("function", "method")}

        for func in analysis.functions:
            caller_id = func.qualified_name or f"{analysis.module_name}.{func.name}"
            for call_name in func.calls:
                target = self._resolve_call(call_name, analysis, all_functions)
                if target:
                    self.graph.add_edge(
                        caller_id,
                        target,
                        edge_type=EdgeType.CALLS.value,
                    )

        for cls in analysis.classes:
            for method in cls.methods:
                caller_id = f"{cls.qualified_name}.{method.name}"
                for call_name in method.calls:
                    target = self._resolve_call(call_name, analysis, all_functions)
                    if target:
                        self.graph.add_edge(
                            caller_id,
                            target,
                            edge_type=EdgeType.CALLS.value,
                        )

    def _add_inheritance_edges(self, analysis: FileAnalysis) -> None:
        for cls in analysis.classes:
            cls_id = cls.qualified_name or f"{analysis.module_name}.{cls.name}"
            for base in cls.bases:
                # Try to resolve base class
                target = self._resolve_class(base, analysis)
                if target and self.graph.has_node(target):
                    self.graph.add_edge(
                        cls_id,
                        target,
                        edge_type=EdgeType.INHERITS.value,
                    )

    def _add_decorator_edges(self, analysis: FileAnalysis) -> None:
        for func in analysis.functions:
            func_id = func.qualified_name or f"{analysis.module_name}.{func.name}"
            for dec in func.decorators:
                # Find decorator if it's a known function
                dec_name = dec.split("(")[0]  # Remove args
                target = self._resolve_call(dec_name, analysis, {})
                if target and self.graph.has_node(target):
                    self.graph.add_edge(
                        target,
                        func_id,
                        edge_type=EdgeType.DECORATES.value,
                    )

    def _resolve_import(self, module: str, analysis: FileAnalysis) -> str | None:
        """Resolve import module name to a file node in the graph."""
        # Try direct module path mapping
        for node_id, data in self.graph.nodes(data=True):
            if data.get("type") == "file" and data.get("module_name") == module:
                return node_id
        # Try partial match
        parts = module.split(".")
        for i in range(len(parts), 0, -1):
            candidate = "/".join(parts[:i]) + ".py"
            if self.graph.has_node(candidate):
                return candidate
            candidate = "/".join(parts[:i]) + "/__init__.py"
            if self.graph.has_node(candidate):
                return candidate
        return None

    def _resolve_call(
        self,
        call_name: str,
        analysis: FileAnalysis,
        all_functions: dict[str, dict],
    ) -> str | None:
        """Best-effort resolution of a call name to a graph node."""
        # Direct match
        if self.graph.has_node(call_name):
            return call_name

        # Try qualified with current module
        qualified = f"{analysis.module_name}.{call_name}"
        if self.graph.has_node(qualified):
            return qualified

        # Try imported names
        for imp in analysis.imports:
            if call_name in imp.names:
                candidate = f"{imp.module}.{call_name}"
                if self.graph.has_node(candidate):
                    return candidate

        # Fuzzy: match by short name
        for node_id, data in all_functions.items():
            if data.get("name") == call_name:
                return node_id

        return None

    def _resolve_class(self, name: str, analysis: FileAnalysis) -> str | None:
        """Resolve a class name reference."""
        for node_id, data in self.graph.nodes(data=True):
            if data.get("type") == "class" and data.get("name") == name:
                return node_id
        return None

    # --- Query methods ---

    def get_file_dependencies(self, file_path: str) -> list[str]:
        """Get files that this file imports from."""
        deps = []
        for _, target, data in self.graph.out_edges(file_path, data=True):
            if data.get("edge_type") == EdgeType.IMPORTS.value:
                deps.append(target)
        return deps

    def get_file_dependents(self, file_path: str) -> list[str]:
        """Get files that import from this file."""
        deps = []
        for source, _, data in self.graph.in_edges(file_path, data=True):
            if data.get("edge_type") == EdgeType.IMPORTS.value:
                deps.append(source)
        return deps

    def get_directory_files(self, dir_path: str) -> list[str]:
        """Get all files in a directory (direct children only)."""
        files = []
        for _, target, data in self.graph.out_edges(dir_path, data=True):
            if data.get("edge_type") == EdgeType.CONTAINS.value:
                node_data = self.graph.nodes[target]
                if node_data.get("type") == "file":
                    files.append(target)
        return files

    def get_node_info(self, node_id: str) -> dict[str, Any] | None:
        if self.graph.has_node(node_id):
            return dict(self.graph.nodes[node_id])
        return None

    def get_all_files(self) -> list[str]:
        return [n for n, d in self.graph.nodes(data=True) if d.get("type") == "file"]

    def get_all_directories(self) -> list[str]:
        return [n for n, d in self.graph.nodes(data=True) if d.get("type") == "directory"]

    # --- Export ---

    def to_json(self) -> dict[str, Any]:
        """Export graph as JSON-serializable dict."""
        nodes = []
        for node_id, data in self.graph.nodes(data=True):
            nodes.append({"id": node_id, **data})

        edges = []
        for source, target, data in self.graph.edges(data=True):
            edges.append({"source": source, "target": target, **data})

        return {"nodes": nodes, "edges": edges}

    def to_mermaid(self, max_nodes: int = 80) -> str:
        """Generate a Mermaid diagram of the graph (file-level only)."""
        lines = ["graph LR"]
        file_nodes = [
            (n, d) for n, d in self.graph.nodes(data=True) if d.get("type") == "file"
        ]

        if len(file_nodes) > max_nodes:
            file_nodes = file_nodes[:max_nodes]
            lines.append(f"    %% Showing first {max_nodes} files")

        # Sanitize node IDs for Mermaid
        def mermaid_id(s: str) -> str:
            return s.replace("/", "_").replace(".", "_").replace("-", "_")

        node_ids = {n for n, _ in file_nodes}
        for node_id, data in file_nodes:
            mid = mermaid_id(node_id)
            label = data.get("name", node_id)
            lines.append(f'    {mid}["{label}"]')

        for source, target, data in self.graph.edges(data=True):
            if source in node_ids and target in node_ids:
                edge_type = data.get("edge_type", "")
                ms = mermaid_id(source)
                mt = mermaid_id(target)
                if edge_type == EdgeType.IMPORTS.value:
                    lines.append(f"    {ms} -->|imports| {mt}")

        return "\n".join(lines)

    def save(self, output_dir: Path) -> None:
        """Save graph artifacts to output directory."""
        output_dir.mkdir(parents=True, exist_ok=True)

        # JSON export
        json_path = output_dir / "knowledge_graph.json"
        json_path.write_text(json.dumps(self.to_json(), indent=2))
        logger.info("Graph JSON saved to %s", json_path)

        # Mermaid export
        mermaid_path = output_dir / "knowledge_graph.mmd"
        mermaid_path.write_text(self.to_mermaid())
        logger.info("Mermaid diagram saved to %s", mermaid_path)

    @classmethod
    def load(cls, output_dir: Path) -> "KnowledgeGraph":
        """Load graph from JSON file."""
        json_path = output_dir / "knowledge_graph.json"
        if not json_path.exists():
            raise FileNotFoundError(f"No graph found at {json_path}")

        data = json.loads(json_path.read_text())
        kg = cls()
        for node in data["nodes"]:
            node_id = node.pop("id")
            kg.graph.add_node(node_id, **node)
        for edge in data["edges"]:
            source = edge.pop("source")
            target = edge.pop("target")
            kg.graph.add_edge(source, target, **edge)

        return kg

    def stats(self) -> dict[str, int]:
        """Return summary statistics."""
        type_counts: dict[str, int] = {}
        for _, data in self.graph.nodes(data=True):
            t = data.get("type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1

        edge_counts: dict[str, int] = {}
        for _, _, data in self.graph.edges(data=True):
            t = data.get("edge_type", "unknown")
            edge_counts[t] = edge_counts.get(t, 0) + 1

        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            **{f"node_{k}": v for k, v in type_counts.items()},
            **{f"edge_{k}": v for k, v in edge_counts.items()},
        }
