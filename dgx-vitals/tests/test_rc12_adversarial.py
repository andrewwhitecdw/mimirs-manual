"""Regressions from the adversarial review of the assembled library."""

import os
import unittest

from tests import support as S


class HealthVerdict(unittest.TestCase):

    def setUp(self):
        self.vit = S.load_vitals()

    def test_zero_healthy_checks_is_incomplete(self):
        state, note = self.vit._verdict_health(
            "0 out of 260 checks are healthy\n"
            "0 out of 260 checks are unhealthy\n")
        self.assertEqual(state, self.vit.INCOMPLETE)
        self.assertIn("no positive healthy-check evidence", note)

    def test_positive_healthy_checks_still_pass(self):
        state, _note = self.vit._verdict_health(
            "260 out of 260 checks are healthy\n"
            "0 out of 260 checks are unhealthy\n")
        self.assertEqual(state, self.vit.PASS)

    def test_skipped_or_unaccounted_checks_are_incomplete(self):
        for text in (
                "259 out of 260 checks are healthy\n"
                "0 out of 260 checks are unhealthy\n"
                "1 out of 260 checks are skipped\n",
                "1 out of 2 checks are healthy\n"
                "0 out of 2 checks are unhealthy\n"):
            with self.subTest(text=text):
                state, _note = self.vit._verdict_health(text)
                self.assertEqual(state, self.vit.INCOMPLETE)


class SSHDestinationValidation(unittest.TestCase):

    def setUp(self):
        self.vit = S.load_vitals()
        self.tmp = S.tempdir(self)

    def test_option_like_destinations_are_rejected(self):
        for kwargs in ({"address": "-oProxyCommand=touch /tmp/pwn"},
                       {"address": "gpu01", "user": "-oProxyCommand=id"},
                       {"address": "gpu 01"}, {"address": "gpu01\n"}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.vit.SSHRunner(**kwargs)

    def test_supported_destinations_still_work(self):
        for address in ("gpu01", "gpu01.example.com", "192.0.2.10", "[2001:db8::10]"):
            with self.subTest(address=address):
                self.assertEqual(self.vit.SSHRunner(address).address, address)
        self.assertEqual(self.vit.SSHRunner("gpu01", user="ops").user, "ops")

    def test_ssh_and_scp_use_end_of_options(self):
        commands = []
        self.vit._exec = lambda cmd, *args, **kwargs: (
            commands.append(cmd) or (0, "", 0.0))
        runner = self.vit.SSHRunner("gpu01", user="ops")
        runner.run(["true"], 30)
        runner.fetch("/tmp/log", os.path.join(self.tmp, "log"))
        for cmd, destination in zip(commands, ("ops@gpu01", "ops@gpu01:/tmp/log")):
            marker = cmd.index("--")
            self.assertEqual(cmd[marker + 1], destination)

    def test_hosts_file_rejects_option_like_address(self):
        path = os.path.join(self.tmp, "hosts.csv")
        with open(path, "w") as f:
            f.write("hostname,address,user\ngpu01,-oProxyCommand=id,ops\n")
        with self.assertRaises(self.vit.HostsFileError):
            self.vit.read_host_entries(path)

    def test_direct_host_error_is_clean_and_writes_nothing(self):
        out = os.path.join(self.tmp, "Results")
        rc, _stdout, stderr = S.run_vitals_main(self.vit, [
            "--host", "gpu01", "--address=-oProxyCommand=id",
            "--dry-run", "--out", out])
        self.assertEqual(rc, 1)
        self.assertIn("unsafe SSH address", stderr)
        self.assertFalse(os.path.exists(out))


class OutputPathContainment(unittest.TestCase):

    def setUp(self):
        self.vit = S.load_vitals()
        self.tmp = S.tempdir(self)

    def test_hostnames_cannot_escape_output_root(self):
        hostile = [os.path.join(self.tmp, "absolute-escape"), "../escape",
                   "a/b", r"a\b", ".", ".."]
        for name in hostile:
            out = os.path.join(self.tmp, "out-" + str(len(os.listdir(self.tmp))))
            with self.subTest(name=name):
                rc, _stdout, stderr = S.run_vitals_main(self.vit, [
                    "--host", name, "--dry-run", "--out", out])
                self.assertEqual(rc, 1)
                self.assertIn("unsafe hostname", stderr)
                self.assertFalse(os.path.exists(out))
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "absolute-escape")))
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "escape")))

    def test_ordinary_hostname_still_dry_runs(self):
        out = os.path.join(self.tmp, "Results")
        rc, _stdout, _stderr = S.run_vitals_main(self.vit, [
            "--host", "gpu01.example.com", "--dry-run", "--out", out])
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.isfile(os.path.join(
            out, "dry-run", "gpu01.example.com",
            "gpu01.example.com-FULLLOG.txt")))

    def test_run_host_also_enforces_containment(self):
        out = os.path.join(self.tmp, "Results")
        with self.assertRaises(self.vit.HostsFileError):
            self.vit.run_host("../escape", S.FakeRunner(), out, [], None)
        self.assertFalse(os.path.exists(out))


class DuplicateHosts(unittest.TestCase):

    def setUp(self):
        self.vit = S.load_vitals()
        self.tmp = S.tempdir(self)
        self.hosts = os.path.join(self.tmp, "hosts.csv")
        with open(self.hosts, "w") as f:
            f.write("hostname,address\ngpu01,192.0.2.1\ngpu01,192.0.2.2\n")

    def test_parser_rejects_duplicate_hostname(self):
        with self.assertRaisesRegex(self.vit.HostsFileError, "duplicate hostname"):
            self.vit.read_host_entries(self.hosts)

    def test_main_creates_no_jobs_or_evidence_for_duplicates(self):
        out = os.path.join(self.tmp, "Results")
        rc, _stdout, stderr = S.run_vitals_main(self.vit, [
            "--hosts", self.hosts, "--dry-run", "--out", out])
        self.assertEqual(rc, 1)
        self.assertIn("duplicate hostname", stderr)
        self.assertFalse(os.path.exists(out))


class SpreadsheetFormulaSafety(unittest.TestCase):

    def setUp(self):
        self.tmp = S.tempdir(self)

    def test_formula_leading_text_is_literal_in_csv_and_xlsx(self):
        for i, host in enumerate(("=1+1", "+cmd", "-cmd", "@cmd", "\tcmd", "\rcmd")):
            with self.subTest(host=host):
                root = S.write_vitals_root(os.path.join(self.tmp, f"r{i}"),
                                           [S.full_dgx(host)])
                sh = S.run_tracker(["--vitals", root], self.tmp, f"t{i}.xlsx")
                safe = "'" + host
                self.assertEqual(sh.get(safe, "Node Hostname"), safe)
                self.assertEqual(sh.csv_row(safe)["Node Hostname"], safe)
                self.assertEqual(sh.get(safe, "% Complete"), 100)


if __name__ == "__main__":
    unittest.main()
