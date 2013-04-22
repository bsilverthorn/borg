import plac
import cPickle as pickle
import borg

logger = borg.get_logger(__name__, default_level="INFO")


@plac.annotations(
    out_path=("path to store portfolio"),
    portfolio_name=("name of the model to train"),
    suite_path=("path to the solver suite"),
    estimate_path=("path to the run data estimate"))
def main(out_path, portfolio_name, suite_path, estimate_path):
    """Train a portfolio."""

    suite = borg.load_solvers(suite_path)

    with borg.util.openz(estimate_path) as estimate_file:
        estimate = pickle.load(estimate_file)

    if portfolio_name == "nearest-rtd":
        regress = borg.regression.NearestRTDRegression(estimate)
        portfolio = borg.portfolios.PureModelPortfolio(suite, estimate, regress)
    else:
        raise ValueError("unrecognized portfolio name")

    with borg.util.openz(out_path, "wb") as out_file:
        pickle.dump(portfolio, out_file)

script_main = borg.script_main(main, __name__)
