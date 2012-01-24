"""@author: Bryan Silverthorn <bcs@cargo-cult.org>"""

import os.path
import subprocess
import condor
import borg

logger = borg.get_logger(__name__, default_level = "DEBUG")

def ground_instance(asp_path, gringo_path, domain_path, ignore_errors):
    """Ground an ASP instance using Gringo."""

    # prepare the gringo invocation
    (asp_path_base, _) = os.path.splitext(asp_path)
    verify_path = "{0}.verify".format(asp_path_base)
    command = [gringo_path, domain_path, asp_path]

    if os.path.exists(verify_path):
        command.append(verify_path)

        verified = " (and verified)"
    else:
        verified = ""

    logger.debug("running %s", command)

    # then ground the instance
    lparse_part_path = "{0}.lparse.part.{1}".format(asp_path, condor.get_process_name())
    lparse_gz_path = "{0}.gz".format(lparse_part_path)

    # XXX cleanup is not robust

    with open(lparse_part_path, "wb") as part_file:
        with open("/dev/null", "wb") as null_file:
            gringo_status = \
                subprocess.call(
                    command,
                    stdout = part_file,
                    stderr = null_file,
                    )

        if gringo_status != 0:
            message = "gringo failed to ground {0}".format(asp_path)

            if ignore_errors:
                logger.warning("%s", message)

                return None
            else:
                raise Exception(message)
        else:
            logger.info("grounded %s%s", asp_path, verified)

    # compress it
    with open(lparse_part_path) as part_file:
        with borg.util.openz(lparse_gz_path, "wb") as gz_file:
            gz_file.write(part_file.read())

    # and move it into place
    lparse_final_path = "{0}.lparse.gz".format(asp_path)

    os.unlink(lparse_part_path)
    os.rename(lparse_gz_path, lparse_final_path)

@borg.annotations(
    gringo_path = ("path to Gringo", "positional", None, os.path.abspath),
    domain_path = ("path the domain file", "positional", None, os.path.abspath),
    root_path = ("instances root directory",),
    ignore_errors = ("ignore Gringo errors", "flag"),
    skip_existing = ("skip already-grounded instances", "flag"),
    workers = ("number of Condor workers", "option", None, int),
    )
def main(gringo_path, domain_path, root_path, ignore_errors = False, skip_existing = False, workers = 0):
    """Ground a set of ASP instances using Gringo."""

    asp_paths = map(os.path.abspath, borg.util.files_under(root_path, "*.asp"))

    def yield_jobs():
        for asp_path in asp_paths:
            if skip_existing and os.path.exists(asp_path + ".lparse.gz"):
                continue

            yield (ground_instance, [asp_path, gringo_path, domain_path, ignore_errors])

    jobs = list(yield_jobs())

    logger.info("grounding %i instances", len(jobs))

    condor.do_for(jobs, workers)

if __name__ == "__main__":
    borg.script(main)
