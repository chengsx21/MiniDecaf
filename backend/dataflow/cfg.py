from backend.dataflow.basicblock import BasicBlock

"""
CFG: Control Flow Graph

nodes: sequence of basicblock
edges: sequence of edge(u,v), which represents after block u is executed, block v may be executed
links: links[u][0] represent the Prev of u, links[u][1] represent the Succ of u,
"""


class CFG:
    def __init__(self, nodes: list[BasicBlock], edges: list[(int, int)]) -> None:
        self.nodes = nodes
        self.edges = edges

        self.links = []
        self.reachability = []
        reachable = [0]

        for i in range(len(nodes)):
            self.links.append((set(), set()))
            self.reachability.append(False)

        for (u, v) in edges:
            self.links[u][1].add(v)
            self.links[v][0].add(u)

        while True:
            if not reachable:
                break
            cur = reachable.pop()
            self.reachability[cur] = True
            for succ in self.getSucc(cur):
                if not self.reachability[succ]:
                    self.reachability[succ] = True
                    reachable.append(succ)

    def getBlock(self, id):
        return self.nodes[id]

    def getPrev(self, id):
        return self.links[id][0]

    def getSucc(self, id):
        return self.links[id][1]

    def getInDegree(self, id):
        return len(self.links[id][0])

    def getOutDegree(self, id):
        return len(self.links[id][1])

    def iterator(self):
        return iter(self.nodes)

    def reachable(self, id):
        return self.reachability[id]
    