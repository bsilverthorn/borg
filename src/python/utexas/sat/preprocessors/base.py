"""
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

def get_named_solvers(paths = [], flags = {}):
    """
    Retrieve a list of named solvers.
    """

    flags = module_flags.merged(flags)

    def yield_preprocessors_from(raw_path):
        """
        (Recursively) yield configured preprocessors.
        """

        import json

        from os.path  import dirname
        from cargo.io import expandpath

        path     = expandpath(raw_path)
        relative = dirname(path)

        with open(path) as file:
            loaded = json.load(file)

        log.note("read named-preprocessors file: %s", raw_path)

        for (name, attributes) in loaded.get("preprocessors", {}).items():
            if name == "sat/SatELite":
                from utexas.sat.preprocessors import SatELitePreprocessor

                yield (name, SatELitePreprocessor(attributes["command"]))
            else:
                raise RuntimeError("unknown preprocessor name \"%s\"" % name)

    # build the solvers dictionary
    from itertools import chain

    return dict(chain(*(yield_preprocessors_from(p) for p in chain(paths, flags.solvers_file))))

class SAT_Preprocessor(ABC):
    """
    Preprocess SAT instances.
    """

    @abstractmethod
    def preprocess(self, task, budget, output_dir, random, environment):
        """
        Preprocess an instance.
        """

    @abstractmethod
    def extend(self, task, answer, environment):
        """
        Extend an answer to a preprocessed task back to its parent task.
        """

    def to_orm(self, session):
        """
        Return the corresponding database description.
        """

        raise RuntimeError("no corresponding database description")

class PreprocessorResult(ABC):
    """
    The result of running a preprocessor.
    """

    @abstractmethod
    def to_orm(self):
        """
        Return an ORM-mapped description of this result.
        """

    def update_orm(self, session, row):
        """
        Set the properties of an ORM-mapped result.
        """

        row.preprocessor = self.preprocessor.to_orm(session)
        row.input_task   = self.input_task.to_orm(session)
        row.output_task  = self.output_task.to_orm(session)
        row.budget       = self.budget
        row.cost         = self.cost
        row.answer       = self.answer.to_orm(session)

    @abstractproperty
    def preprocessor(self):
        """
        The preprocessor that generated this result.
        """

    @abstractproperty
    def input_task(self):
        """
        The task on which this result was obtained.
        """

    @abstractproperty
    def output_task(self):
        """
        The task generated by the preprocessor, if any.
        """

    @abstractproperty
    def budget(self):
        """
        The budget provided for obtaining this result.
        """

    @abstractproperty
    def cost(self):
        """
        The cost of obtaining this result.
        """

    @abstractproperty
    def answer(self):
        """
        The result of the integrated solver, if any.
        """

class PreprocessorRunResult(PreprocessorResult):
    """
    The result of running a concrete preprocessor binary.
    """

    @abstractproperty
    def run(self):
        """
        The details of the associated run.
        """

class BarePreprocessorResult(PreprocessorResult):
    """
    A typical preprocessor result implementation.
    """

    def __init__(self, preprocessor, input_task, output_task, budget, cost, answer):
        """
        Initialize.
        """

        PreprocessorResult.__init__(self)

        self._preprocessor = preprocessor
        self._input_task   = input_task
        self._output_task  = output_task
        self._budget       = budget
        self._cost         = cost
        self._answer       = answer

    def to_orm(self):
        """
        Return an ORM-mapped description of this result.
        """

        raise NotImplementedError()

    @property
    def preprocessor(self):
        """
        The preprocessor that generated this result.
        """

        return self._preprocessor

    @property
    def input_task(self):
        """
        The task on which this result was obtained.
        """

        return self._input_task

    @property
    def output_task(self):
        """
        The task generated by the preprocessor, if any.
        """

        return self._output_task

    @property
    def budget(self):
        """
        The budget provided for obtaining this result.
        """

        return self._budget

    @property
    def cost(self):
        """
        The cost of obtaining this result.
        """

        return self._cost

    @property
    def answer(self):
        """
        The result of the integrated solver, if any.
        """

        return self._answer

class BarePreprocessorRunResult(BarePreprocessorResult, PreprocessorRunResult):
    """
    A typical preprocessor run result implementation.
    """

    def __init__(self, preprocessor, input_task, output_task, answer, run):
        """
        Initialize.
        """

        BarePreprocessorResult.__init__(
            self,
            preprocessor,
            input_task,
            output_task,
            run.limit,
            run.proc_elapsed,
            answer,
            )

        self._run = run

    @property
    def run(self):
        """
        The details of the associated run.
        """

        return self._run

class WrappedPreprocessorResult(PreprocessorResult):
    """
    The result of a wrapped preprocessor.
    """

    def __init__(self, preprocessor, inner_result):
        """
        Initialize.
        """

        self._preprocessor = preprocessor
        self._inner        = inner_result

    def to_orm(self):
        """
        Return an ORM-mapped description of this result.
        """

        raise NotImplementedError()

    @property
    def preprocessor(self):
        """
        The preprocessor that generated this result.
        """

        return self._preprocessor

    @property
    def input_task(self):
        """
        The task on which this result was obtained.
        """

        return self._inner.input_task

    @property
    def output_task(self):
        """
        The task generated by the preprocessor, if any.
        """

        return self._inner.output_task

    @property
    def budget(self):
        """
        The budget provided for obtaining this result.
        """

        return self._inner.budget

    @property
    def cost(self):
        """
        The cost of obtaining this result.
        """

        return self._inner.cost

    @property
    def answer(self):
        """
        The result of the integrated solver, if any.
        """

        return self._inner.answer

class SAT_PreprocessorError(RuntimeError):
    """
    The preprocessor failed in an unexpected way.
    """

