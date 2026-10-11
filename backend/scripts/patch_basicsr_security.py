"""Patch BasicSR's SLURM shell injection (CVE-2024-27763) at install time.

The pinned upstream package has no patched release. Fail the build if its source
changes, so an upstream update cannot silently drop this mitigation.
"""

import argparse
from importlib.metadata import distribution


UNSAFE = (
    "    addr = subprocess.getoutput(f'scontrol show hostname {node_list} | head -n1')"
)
SAFE = """    # Viddie: CVE-2024-27763, never interpolate a host list into a shell.
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.,[]-"
    if not node_list or node_list.startswith("-") or any(c not in allowed for c in node_list):
        raise ValueError("Invalid SLURM_NODELIST")
    addr = subprocess.check_output(
        ["scontrol", "show", "hostname", node_list], text=True
    ).splitlines()[0]"""


def patch_source(source):
    if SAFE in source and UNSAFE not in source:
        return source
    if source.count(UNSAFE) != 1:
        raise RuntimeError(
            "BasicSR security patch needs review: unexpected SLURM helper"
        )
    return source.replace(UNSAFE, SAFE)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify without modifying the installed package",
    )
    options = parser.parse_args()
    target = distribution("basicsr").locate_file("basicsr/utils/dist_util.py")
    source = target.read_text()
    patched = patch_source(source)
    compile(patched, str(target), "exec")
    if patched != source:
        if options.check:
            raise RuntimeError("BasicSR security patch is missing")
        target.write_text(patched)
    print("BasicSR CVE-2024-27763 patch verified")


if __name__ == "__main__":
    main()
