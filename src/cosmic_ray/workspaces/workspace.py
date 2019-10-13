import abc


class Workspace:
    @abc.abstractmethod
    def cleanup(self):
        pass

    @property
    @abc.abstractmethod
    def clone_dir(self):
        pass
