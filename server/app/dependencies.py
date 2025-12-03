# Global node instance to be set by main
_node_instance = None


def get_node():
    """Dependency to get the current node instance."""
    return _node_instance


def set_node_instance(node):
    """Set the global node instance."""
    global _node_instance
    _node_instance = node
