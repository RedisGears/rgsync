import os
import toml

def find_package():
    """Find the appropriate package for installation."""

    # build the path to the built rgsync, as it is in the docker
    ll = toml.load("pyproject.toml")
    version = ll['tool']['poetry']['version']
    rgsync_pkg =  "rgsync-{}-py3-none-any.whl".format(version)

    # determine whether or not we're running in a docker
    in_docker = False
    if os.path.isfile("/.dockerenv") or \
        os.environ.get("IN_DOCKER", None) is not None:
        in_docker = True

    # install package
    if in_docker:
        pkg = os.path.join("/build", "dist", rgsync_pkg)
    else:
        if os.path.join(os.getcwd(), "dist", rgsync_pkg):
            pkg = os.path.join(os.getcwd(), "dist", rgsync_pkg)
        else:
            pkg = "rgsync"

    return pkg

def to_utf(d):
    if isinstance(d, str):
        return d.encode('utf-8')
    if isinstance(d, dict):
        return {to_utf(k): to_utf(v) for k, v in d.items()}
    if isinstance(d, list):
        return [to_utf(x) for x in d]
    return d