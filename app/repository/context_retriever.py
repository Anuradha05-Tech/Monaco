class ContextRetriever:
    """
    Retrieves contextually related files based on a dependency graph.

    It finds files related to a target file by traversing imports in both directions
    (files imported by target, and files that import target) up to a specified depth.
    """

    def __init__(self, graph: dict[str, list[str]]):
        """
        Initializes the ContextRetriever with a dependency graph.

        Args:
            graph: A dictionary mapping file paths (relative to repo root) to a list of
                   their resolved import file paths.
        """
        self.graph = graph

    def get_related_files(self, target_file: str, depth: int = 1) -> list[str]:
        """
        Returns a list of files related to the target file up to a certain depth.

        It traverses the dependency graph in both directions (in-edges and out-edges).

        Args:
            target_file: The relative path of the file to find relations for.
            depth: The maximum number of hops to traverse in the graph (default: 1).
                   Warning: Deeper values (e.g., depth >= 2) may pull in large parts
                   of the repository as the traversal expands bidirectional relations.

        Returns:
            A sorted, deduplicated list of related file paths (relative to repo root).
            If the target file is not in the graph, returns an empty list.
        """
        # Collect all nodes that are present in the graph (either as keys or values)
        nodes = set(self.graph.keys())
        for imports in self.graph.values():
            nodes.update(imports)

        if target_file not in nodes:
            return []

        # Build bidirectional (undirected) adjacency list
        adj = {node: set() for node in nodes}
        for node, imports in self.graph.items():
            for imp in imports:
                adj[node].add(imp)
                adj[imp].add(node)

        # BFS to find all unique reachable nodes up to 'depth' hops
        visited = {target_file}
        current_layer = {target_file}

        for _ in range(depth):
            next_layer = set()
            for node in current_layer:
                for neighbor in adj.get(node, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        next_layer.add(neighbor)
            current_layer = next_layer
            if not current_layer:
                break

        # Exclude the target file itself
        visited.discard(target_file)

        return sorted(list(visited))
