"""
utexas/sat/solvers/base.py

@author: Bryan Silverthorn <bcs@cargo-cult.org>
"""

from abc         import (
    abstractmethod,
    abstractproperty,
    )
from cargo.log   import get_logger
from cargo.sugar import ABC
from cargo.flags import (
    Flag,
    Flags,
    )

log          = get_logger(__name__)
module_flags = \
    Flags(
        "SAT Solver Configuration",
        Flag(
            "--solvers-file",
            default = [],
            action  = "append",
            metavar = "FILE",
            help    = "read solver descriptions from FILE [%default]",
            ),
        )

def get_random_seed(random):
    """
    Return a random solver seed.
    """

    return random.randint(2**31 - 1)

def get_named_solvers(paths = [], flags = {}):
    """
    Retrieve a list of named solvers.
    """

    import json

    from os.path            import dirname
    from cargo.io           import expandpath
    from utexas.sat.solvers import SAT_CompetitionSolver

    flags = module_flags.merged(flags)

    def yield_solvers_from(raw_path):
        """
        (Recursively) yield solvers from a solvers file.
        """

        path     = expandpath(raw_path)
        relative = dirname(path)

        with open(path) as file:
            loaded = json.load(file)

        log.note("read named-solvers file: %s", raw_path)

        for (name, attributes) in loaded.get("solvers", {}).items():
            yield (
                name,
                SAT_CompetitionSolver(
                    attributes["command"],
                    solvers_home = relative,
                    name         = name,
                    ),
                )

        for included in loaded.get("includes", []):
            for solver in yield_solvers_from(expandpath(included, relative)):
                yield solver

    # build the solvers dictionary
    from itertools import chain

    return dict(chain(*(yield_solvers_from(p) for p in chain(paths, flags.solvers_file))))

class AbstractSolver(AbstractRowed):
    """
    A solver for SAT.
    """

    @abstractmethod
    def solve(self, task, budget, random, environment):
        """
        Attempt to solve the specified instance; return the outcome.
        """

class SAT_Environment(object):
    """
    Execution-specific properties of SAT solver execution.
    """

    def __init__(
        self,
        time_ratio          = 1.0,
        named_solvers       = None,
        named_preprocessors = None,
        collections         = {},
        MainSession         = None,
        CacheSession        = None,
        ):
        """
        Initialize.
        """

        self.time_ratio          = time_ratio
        self.named_solvers       = named_solvers
        self.named_preprocessors = named_preprocessors
        self.collections         = collections
        self.MainSession         = MainSession
        self.CacheSession        = CacheSession

class AbstractAttempt(object):
    """
    Outcome of a SAT solver.
    """

    @abstractmethod
    def to_orm(self):
        """
        Return an ORM-mapped description of this result.
        """

    def update_orm(self, session, row):
        """
        Set the properties of an ORM-mapped description.
        """

        row.budget      = self.budget
        row.cost        = self.cost
        row.satisfiable = self.satisfiable
        row.task        = self.task.to_orm(session)

        row.set_certificate(self.certificate)

        return row

    @abstractproperty
    def solver(self):
        """
        The solver that obtained this result.
        """

    @abstractproperty
    def task(self):
        """
        The task on which this result was obtained.
        """

    @abstractproperty
    def budget(self):
        """
        The budget provided to the solver to obtain this result.
        """

    @abstractproperty
    def cost(self):
        """
        The cost of obtaining this result.
        """

    @abstractproperty
    def satisfiable(self):
        """
        Did the solver report the instance satisfiable?
        """

    @abstractproperty
    def certificate(self):
        """
        Certificate of satisfiability, if any.
        """

class SAT_BareResult(SAT_Result):
    """
    Minimal outcome of a SAT solver.
    """

    def __init__(self, solver, task, budget, cost, satisfiable, certificate):
        """
        Initialize.
        """

        SAT_Result.__init__(self)

        self._solver      = solver
        self._task        = task
        self._budget      = budget
        self._cost        = cost
        self._satisfiable = satisfiable
        self._certificate = certificate

    def to_orm(self):
        """
        Return a database description of this result.
        """

        return self.update_orm(SAT_AttemptRow())

    @abstractproperty
    def solver(self):
        """
        The solver which obtained this result.
        """

        return self._solver

    @abstractproperty
    def task(self):
        """
        The task on which this result was obtained.
        """

        return self._task

    @abstractproperty
    def budget(self):
        """
        The budget provided to the solver to obtain this result.
        """

        return self._budget

    @abstractproperty
    def cost(self):
        """
        The cost of obtaining this result.
        """

        return self._cost

    @property
    def satisfiable(self):
        """
        Did the solver report the instance satisfiable?
        """

        return self._satisfiable

    @property
    def certificate(self):
        """
        Certificate of satisfiability, if any.
        """

        return self._certificate

class SAT_WrappedResult(SAT_Result):
    """
    A result from an inner solver.
    """

    def __init__(self, solver, inner_result):
        """
        Initialize.
        """

        SAT_Result.__init__(self)

        self._solver       = solver
        self._inner_result = inner_result

    def to_orm(self):
        """
        Return a database description of this result.
        """

        return self._inner_result.to_orm()

    @abstractproperty
    def solver(self):
        """
        The solver which obtained this result.
        """

        return self._solver

    @abstractproperty
    def task(self):
        """
        The task on which this result was obtained.
        """

        return self._inner_result.task

    @abstractproperty
    def budget(self):
        """
        The budget provided to the solver to obtain this result.
        """

        return self._inner_result.budget

    @abstractproperty
    def cost(self):
        """
        The cost of obtaining this result.
        """

        return self._inner_result.cost

    @property
    def satisfiable(self):
        """
        Did the solver report the instance satisfiable?
        """

        return self._inner_result.satisfiable

    @property
    def certificate(self):
        """
        Certificate of satisfiability, if any.
        """

        return self._inner_result.certificate

class SolverError(RuntimeError):
    """
    The solver failed in an unexpected way.
    """

