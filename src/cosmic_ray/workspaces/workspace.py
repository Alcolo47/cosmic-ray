import abc

from cosmic_ray.workspaces.cloner import Cloner


class Workspace:
    def __init__(self, cloner: Cloner):
        self.cloner = cloner

    # @abc.abstractmethod
    # def cleanup(self):
    #     pass

    @property
    @abc.abstractmethod
    def clone_dir(self):
        pass
