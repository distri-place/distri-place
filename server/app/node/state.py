from enum import Enum


class NodeState(Enum):
    STARTING = "starting"
    ACTIVE = "active"
    STOPPING = "stopping"
    STOPPED = "stopped"


class NodeStateManager:
    def __init__(self):
        self.state = NodeState.STARTING

    def transition_to(self, new_state: NodeState):
        pass

    def get_state(self) -> NodeState:
        return self.state
