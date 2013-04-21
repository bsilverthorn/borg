import plac
import cPickle as pickle
import borg

logger = borg.get_logger(__name__, default_level="INFO")


@plac.annotations(
    out_path=("path to store estimates"),
    estimator_name=("name of the estimator to use"),
    bundle_path=("path to the run data bundle"),
    bins=("number of discrete bins", "option", None, int))
def main(out_path, estimator_name, bundle_path, bins=30):
    """Estimate run time distributions from incomplete data."""

    estimator_makers = {
        "multinomial": borg.models.MulEstimator,
        "dirichlet": borg.models.MulDirMatMixEstimator}

    try:
        make_estimator = estimator_makers[estimator_name]
    except KeyError:
        raise ValueError("unrecognized estimator")

    estimator = make_estimator()
    run_data = borg.storage.RunData.from_bundle(bundle_path)
    run_data = run_data.only_nontrivial(run_data.common_budget / bins)
    estimate = estimator(run_data, bins, run_data)

    with borg.util.openz(out_path, "wb") as out_file:
        logger.info("writing %s to %s", estimate, out_path)

        pickle.dump(estimate, out_file)

script_main = borg.script_main(main, __name__)
