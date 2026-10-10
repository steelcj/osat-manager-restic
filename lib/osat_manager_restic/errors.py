"""The one exception manage-restic raises for anything it refuses to do."""


class ManagerError(Exception):
    """A request the manager will not carry out; the command line turns it
    into a message and exit status 1."""
