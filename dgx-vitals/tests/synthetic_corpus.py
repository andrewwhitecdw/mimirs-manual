"""Rebuild deterministic synthetic FULLLOGs missing from the field corpus."""

import os

from tests import support as S


HOSTS = {
    "full-w08-hollow-stress": ("fx-w08-prod-hv-01",),
    "wave1-w08-already-running": ("fx-w08-prod-hv-01",),
    "wave1-w09-full-pass": ("fx-w09-prod-hv-01",),
    "wave1-x10-ki2": ("fx-x10-prod-hv-01",),
    "xwave2-no-summary": ("fx-x01-prod-hv-02", "fx-x01-prod-hv-04"),
    "y10-truncated": ("fx-y10-prod-hv-02",),
}

STRESS_PASS = """Stress Test Log: /var/nvsmlog/nvsm/StressTestLog2026-11-12T01:12:53Z.nvsmlog
GPU            PASS
CPU            PASS
Memory         PASS
Storage        PASS
PCIe           PASS
100% Complete"""

STRESS_GPU_FAILED = STRESS_PASS.replace("GPU            PASS", "GPU            Failed")

HOLLOW_STRESS = """Are you sure you want to proceed? [y/N]
Stress test cancelled."""

ALREADY_RUNNING = """Stress test is already running.
User preference is 'cancel'."""


def field_health(extra_psu=False):
    bundle = "cdw-validation-fx-w09-prod-hv-01-20261111-174304"
    text = S.read_fixture("bundle-w09", "fx-w09-prod-hv-01", bundle,
                          "04-nvsm-health.log")
    if extra_psu:
        text = text.replace(
            "Check PSU Info (Vendor, Model) for Consistency"
            "....................... Healthy",
            "Check PSU Info (Vendor, Model) for Consistency"
            "....................... Unhealthy")
        text = text.replace("259 out of 260 checks are healthy",
                            "258 out of 260 checks are healthy")
        text = text.replace("1 out of 260 checks are unhealthy",
                            "2 out of 260 checks are unhealthy")
    return text


def missing_nccl():
    out = []
    for name in ("all_reduce", "all_gather", "reduce_scatter"):
        out += [f"===== {name}_perf =====",
                "8 total processes failed to start",
                "mpirun was unable to find the specified executable file, "
                "and therefore did not launch the job.",
                "Node:       fx-gpu",
                f"Executable: {name}_perf",
                f"[{name}_perf exit 134]"]
    return "\n".join(out)


def base_sections(health=None):
    sections = list(S.DGX_SECTIONS)
    sections[3] = ("topo", S.topo_matrix(8), "PASS", "8 GPUs, all 28 GPU pairs NV18")
    sections[5] = ("dump", "The output of this command is written to: "
                   "/tmp/nvsm-health-fx.tar.xz", "PASS", "archive written")
    if health is not None:
        sections[1] = ("health", health, "FAIL",
                       "output mentions: unhealthy")
    return sections


def with_nccl(sections, body, state, note):
    return sections[:4] + [("nccl", body, state, note)] + sections[4:]


def make_log(case, host):
    tool = {
        "full-w08-hollow-stress": "dgx-vitals.py v1.4",
        "wave1-w08-already-running": "dgx-vitals.py v1.5",
        "wave1-w09-full-pass": "dgx-vitals.py v1.5",
        "wave1-x10-ki2": "dgx-vitals.py v1.5",
    }.get(case, "dgx-vitals.py v1.9")
    overall = None
    planned = None

    if case == "full-w08-hollow-stress":
        sections = with_nccl(
            base_sections(field_health()), missing_nccl(), "FAIL",
            "all_reduce: exit 134; all_gather: exit 134; reduce_scatter: exit 134")
        sections[5] = ("stress", HOLLOW_STRESS, "PASS", "5/5 components PASS")
        sections[6] = ("dump", "dump timed out", "FAIL", "exit code 124", 124)
    elif case == "wave1-w08-already-running":
        sections = with_nccl(
            base_sections(field_health(extra_psu=True)), "", "SKIP",
            "nccl-tests not installed on this host — step skipped")
        sections[5] = ("stress", ALREADY_RUNNING, "PASS", "5/5 components PASS")
    elif case == "wave1-w09-full-pass":
        sections = with_nccl(
            base_sections(field_health()), missing_nccl(), "FAIL",
            "all_gather: exit 134; not installed: all_reduce, reduce_scatter "
            "(nccl-tests partially provisioned)")
        sections[5] = ("stress", STRESS_PASS, "PASS",
                       "5/5 components PASS, 100% Complete, 1827s")
    elif case == "wave1-x10-ki2":
        sections = with_nccl(
            base_sections(field_health()), missing_nccl(), "FAIL",
            "all_reduce: exit 134; not installed: all_gather, reduce_scatter "
            "(nccl-tests partially provisioned)")
        sections[5] = ("stress", STRESS_PASS, "PASS",
                       "5/5 components PASS, 100% Complete, 1827s")
        sections[6] = ("dump", "scp failed", "FAIL", "exit code 255", 255)
    elif case == "xwave2-no-summary":
        sections = base_sections(field_health())
        if host.endswith("02"):
            sections[4] = ("stress", "Stress test FAILED: 2 GPU errors", "FAIL",
                           "stress output mentions fail/error — check FULLLOG")
        else:
            sections[4] = ("stress", STRESS_PASS, "PASS",
                           "5/5 components PASS, 100% Complete, 1827s")
    elif case == "y10-truncated":
        sections = base_sections(field_health())[:4]
        sections.append(("stress", STRESS_GPU_FAILED, "FAIL",
                         "component(s) not PASS: GPU Failed"))
        overall = False
        planned = 6
    else:
        raise KeyError(case)

    text = S.runner_fulllog(host, sections, overall=overall, tool=tool,
                            planned=planned)
    marker = "Fixture: deterministic synthetic parser evidence; not hardware output\n"
    return text.replace("DGX Vitals — FULLLOG\n",
                        "DGX Vitals — FULLLOG\n" + marker, 1)


def main():
    for case, hosts in HOSTS.items():
        for host in hosts:
            directory = os.path.join(S.FIXTURES, case, host)
            os.makedirs(directory, exist_ok=True)
            path = os.path.join(directory, f"{host}-FULLLOG.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(make_log(case, host))
            print(os.path.relpath(path, S.REPO))


if __name__ == "__main__":
    main()
