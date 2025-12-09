from app.canvas.state import Canvas
from app.raft.node import RaftNode

_node_instance = None
_canvas_instance = None
_client_manager_instance = None


def get_node_instance():
    return _node_instance


def get_canvas_instance():
    return _canvas_instance


def get_client_manager_instance():
    return _client_manager_instance


def set_node_instance(node: RaftNode):
    global _node_instance
    _node_instance = node


def set_canvas_instance(canvas: Canvas):
    global _canvas_instance
    _canvas_instance = canvas


def set_client_manager_instance(manager):
    global _client_manager_instance
    _client_manager_instance = manager
