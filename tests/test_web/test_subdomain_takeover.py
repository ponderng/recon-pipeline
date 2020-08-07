import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pipeline.recon.web import SubjackScan, TKOSubsScan, GatherWebTargets

subjack_results = Path(__file__).parent.parent / "data" / "recon-results" / "subjack-results"
tkosubs_results = Path(__file__).parent.parent / "data" / "recon-results" / "tkosubs-results"


class TestTKOSubsScanScan:
    def setup_method(self):
        self.tmp_path = Path(tempfile.mkdtemp())
        self.scan = TKOSubsScan(
            target_file=__file__, results_dir=str(self.tmp_path), db_location=str(self.tmp_path / "testing.sqlite")
        )
        self.scan.exception = False

    def teardown_method(self):
        shutil.rmtree(self.tmp_path)

    def test_scan_requires(self):
        with patch("pipeline.recon.web.GatherWebTargets"):
            with patch("pipeline.recon.web.subdomain_takeover.meets_requirements"):
                retval = self.scan.requires()
                assert isinstance(retval, GatherWebTargets)

    def test_scan_creates_results_dir(self):
        assert self.scan.results_subfolder == self.tmp_path / "tkosubs-results"

    def test_scan_creates_results_file(self):
        assert self.scan.output_file == self.tmp_path / "tkosubs-results" / "tkosubs.csv"

    def test_scan_creates_database(self):
        assert self.scan.db_mgr.location.exists()
        assert self.tmp_path / "testing.sqlite" == self.scan.db_mgr.location

    def test_scan_creates_results(self):
        self.scan.results_subfolder = tkosubs_results
        self.scan.output_file = self.scan.results_subfolder / "tkosubs.csv"
        self.scan.parse_results()
        assert self.scan.output().exists()

    def test_parse_results(self):
        myresults = self.tmp_path / "tkosubs-results" / "tkosubs.csv"
        myresults.parent.mkdir(parents=True, exist_ok=True)

        content = "Domain,Cname,Provider,IsVulnerable,IsTakenOver,Response\n"
        content += "google.com,Cname,Provider,true,IsTakenOver,Response\n"
        content += "maps.google.com,Cname,Provider,false,IsTakenOver,Response\n"

        myresults.write_text(content)

        self.scan.output_file = myresults
        self.scan.db_mgr.get_or_create_target_by_ip_or_hostname = MagicMock()
        self.scan.db_mgr.get_or_create_target_by_ip_or_hostname.return_value = MagicMock()
        self.scan.db_mgr.add = MagicMock()

        self.scan.parse_results()
        assert self.scan.output().exists()
        assert self.scan.db_mgr.add.called
        assert self.scan.db_mgr.get_or_create_target_by_ip_or_hostname.called

    @pytest.mark.parametrize("test_input", [["google.com"], None])
    def test_scan_run(self, test_input):
        with patch("subprocess.run") as mocked_run:
            self.scan.parse_results = MagicMock()
            self.scan.db_mgr.get_all_hostnames = MagicMock()
            self.scan.db_mgr.get_all_hostnames.return_value = test_input

            self.scan.run()
            if test_input is None:
                assert not mocked_run.called
                assert not self.scan.parse_results.called
            else:
                assert mocked_run.called
                assert self.scan.parse_results.called


class TestSubjackScan:
    def setup_method(self):
        self.tmp_path = Path(tempfile.mkdtemp())
        self.scan = SubjackScan(
            target_file=__file__, results_dir=str(self.tmp_path), db_location=str(self.tmp_path / "testing.sqlite")
        )
        self.scan.exception = False

    def teardown_method(self):
        shutil.rmtree(self.tmp_path)

    def test_scan_requires(self):
        with patch("pipeline.recon.web.GatherWebTargets"):
            with patch("pipeline.recon.web.subdomain_takeover.meets_requirements"):
                retval = self.scan.requires()
                assert isinstance(retval, GatherWebTargets)

    def test_scan_creates_results_dir(self):
        assert self.scan.results_subfolder == self.tmp_path / "subjack-results"

    def test_scan_creates_results_file(self):
        assert self.scan.output_file == self.tmp_path / "subjack-results" / "subjack.txt"

    def test_scan_creates_database(self):
        assert self.scan.db_mgr.location.exists()
        assert self.tmp_path / "testing.sqlite" == self.scan.db_mgr.location

    def test_scan_creates_results(self):
        self.scan.results_subfolder = subjack_results
        self.scan.output_file = self.scan.results_subfolder / "subjack.txt"
        self.scan.parse_results()
        assert self.scan.output().exists()

    def test_parse_results(self):
        myresults = self.tmp_path / "subjack-results" / "subjack.txt"
        myresults.parent.mkdir(parents=True, exist_ok=True)

        content = "[Not Vulnerable] email.assetinventory.bugcrowd.com\n"
        content += "[Vulnerable] email.assetinventory.bugcrowd.com\n"
        content += "[Vulnerable] assetinventory.bugcrowd.com:8080\n"
        content += "weird input\n"

        myresults.write_text(content)

        self.scan.output_file = myresults
        self.scan.db_mgr.get_or_create_target_by_ip_or_hostname = MagicMock()
        self.scan.db_mgr.get_or_create_target_by_ip_or_hostname.return_value = MagicMock()
        self.scan.db_mgr.add = MagicMock()

        self.scan.parse_results()
        assert self.scan.output().exists()
        assert self.scan.db_mgr.add.called
        assert self.scan.db_mgr.get_or_create_target_by_ip_or_hostname.called

    @pytest.mark.parametrize("test_input", [["google.com"], None])
    def test_scan_run(self, test_input):
        with patch("subprocess.run") as mocked_run:
            self.scan.parse_results = MagicMock()
            self.scan.db_mgr.get_all_hostnames = MagicMock()
            self.scan.db_mgr.get_all_hostnames.return_value = test_input

            self.scan.run()
            if test_input is None:
                assert not mocked_run.called
                assert not self.scan.parse_results.called
            else:
                assert mocked_run.called
                assert self.scan.parse_results.called
