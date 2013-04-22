import plac
import sys
import logging
import cPickle as pickle
import borg

logger = borg.get_logger(__name__, default_level="INFO")


class CompetitionFormatter(logging.Formatter):
    """A concise log formatter for output during competition."""

    def __init__(self):
        logging.Formatter.__init__(self, "%(levelname)s: %(message)s", "%y%m%d%H%M%S")

    def format(self, record):
        """Format the log record."""

        raw = logging.Formatter.format(self, record)

        def yield_lines():
            lines  = raw.splitlines()
            indent = "c " + " " * (len(record.levelname) + 2)

            yield "c " + lines[0]

            for line in lines[1:]:
                yield indent + line

        return "\n".join(yield_lines())

def enable_output():
    """Set up competition-compliant output."""

    # configure the default global level
    borg.get_logger(level = borg.defaults.root_log_level)

    # set up output
    handler = logging.StreamHandler(sys.stdout)

    handler.setFormatter(CompetitionFormatter())
    handler.setLevel(logging.NOTSET)

    logging.root.addHandler(handler)

@plac.annotations(
    portfolio_path = ("path to trained portfolio"),
    suite_path = ("path to solver suite"),
    instance_path = ("path to instance"),
    seed = ("PRNG seed", "option", None, int),
    budget = ("time limit (CPU or wall)", "option", None, float),
    cores = ("units of execution", "option", None, int),
    speed = ("machine calibration ratio", "option", "s", float),
    quiet = ("be less noisy", "flag", "q"))
def main(
        portfolio_path,
        suite_path,
        instance_path,
        seed = 42,
        budget = 3600.0,
        cores = 1,
        speed = borg.defaults.machine_speed,
        quiet = False):
    """Solve a problem instance."""

    # XXX hackish
    borg.defaults.machine_speed = speed

    try:
        # general setup
        enable_output()

        if not quiet:
            borg.get_logger("borg.solvers", level="DETAIL")

        borg.statistics.set_prng_seeds(seed)

        # run the solver
        suite = borg.load_solvers(suite_path)

        logger.info("loading portfolio %s", portfolio_path)

        with open(portfolio_path) as portfolio_file:
            portfolio = pickle.load(portfolio_file)

        solver = borg.solver_io.RunningPortfolioFactory(portfolio, suite)

        logger.info("solving %s", instance_path)

        with suite.domain.task_from_path(instance_path) as task:
            remaining = budget - borg.get_accountant().total.cpu_seconds
            answer = solver.start(task).run_then_stop(remaining)

            return bundle.domain.show_answer(task, answer)
    except KeyboardInterrupt:
        print "\nc terminating on SIGINT"

script_main = borg.script_main(main, __name__, logging=False)
