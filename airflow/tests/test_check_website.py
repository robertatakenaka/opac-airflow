import tempfile
import shutil
import pathlib
import os
from unittest import TestCase, main
from unittest.mock import patch, MagicMock, ANY, call

import pendulum
from airflow import DAG

from check_website import (
    get_file_path_in_proc_dir,
    check_website_uri_list,
    get_uri_list_file_paths,
    get_uri_items_from_uri_list_files,
    get_pid_list_csv_file_paths,
    get_uri_items_from_pid_list_csv_files,
    join_and_group_uri_items_by_script_name,
    check_sci_serial_uri_items,
    check_sci_issues_uri_items,
    check_sci_issuetoc_uri_items,
    get_pid_v3_list,
    get_website_url_list,
)


class TestGetFilePathInProcDir(TestCase):
    def setUp(self):
        self.gate_dir = tempfile.mkdtemp()
        self.proc_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.gate_dir)
        shutil.rmtree(self.proc_dir)

    def test_uri_list_does_not_exist_in_origin(self):
        with self.assertRaises(FileNotFoundError) as exc_info:
            get_file_path_in_proc_dir(
                pathlib.Path("no/dir/path"),
                pathlib.Path(self.proc_dir),
                "uri_list_2020-12-31.lst",
            )
        self.assertIn("no/dir/path/uri_list_2020-12-31.lst", str(exc_info.exception))

    def test_uri_list_already_exists_in_proc(self):
        uri_list_path_origin = pathlib.Path(self.gate_dir) / "uri_list_2020-01-01.lst"
        uri_list_path_origin.write_text("/scielo.php?script=sci_serial&pid=1234-5678")
        uri_list_path_proc = pathlib.Path(self.proc_dir) / "uri_list_2020-01-01.lst"
        uri_list_path_proc.write_text("/scielo.php?script=sci_serial&pid=5678-0909")
        _uri_list_file_path = get_file_path_in_proc_dir(
            pathlib.Path(self.gate_dir),
            pathlib.Path(self.proc_dir),
            "uri_list_2020-01-01.lst",
        )

        self.assertEqual(
            _uri_list_file_path,
            str(pathlib.Path(self.proc_dir) / "uri_list_2020-01-01.lst")
        )
        self.assertEqual(uri_list_path_proc.read_text(), "/scielo.php?script=sci_serial&pid=5678-0909")

    def test_uri_list_must_be_copied(self):
        uri_list_path = pathlib.Path(self.gate_dir) / "uri_list_2020-01-01.lst"
        uri_list_path.write_text("/scielo.php?script=sci_serial&pid=5678-0909")
        _uri_list_file_path = get_file_path_in_proc_dir(
            pathlib.Path(self.gate_dir),
            pathlib.Path(self.proc_dir),
            "uri_list_2020-01-01.lst",
        )
        self.assertEqual(
            _uri_list_file_path,
            str(pathlib.Path(self.proc_dir) / "uri_list_2020-01-01.lst")
        )


class TestGetUriListFilePaths(TestCase):

    def setUp(self):
        self.kwargs = {
            "ti": MagicMock(),
            "conf": None,
            "run_id": "test_run_id",
        }
        self.gate_dir = tempfile.mkdtemp()
        self.proc_dir = tempfile.mkdtemp()
        self.dag_proc_dir = str(pathlib.Path(self.proc_dir) / "test_run_id")
        os.makedirs(self.dag_proc_dir)
        for f in ("uri_list_2020-01-01.lst", "uri_list_2020-01-02.lst", "uri_list_2020-01-03.lst"):
            file_path = pathlib.Path(self.gate_dir) / f
            with open(file_path, "w") as fp:
                fp.write("")
        for f in ("any_2020-01-01.lst", "any_2020-01-02.lst", "any_2020-01-03.lst"):
            file_path = pathlib.Path(self.gate_dir) / f
            with open(file_path, "w") as fp:
                fp.write("")
        for f in ("any_2020-01-01.lst", "any_2020-01-02.lst", "any_2020-01-03.lst"):
            file_path = pathlib.Path(self.dag_proc_dir) / f
            with open(file_path, "w") as fp:
                fp.write("")

    def tearDown(self):
        shutil.rmtree(self.gate_dir)
        shutil.rmtree(self.proc_dir)

    @patch("check_website.Variable.get")
    def test_get_uri_list_file_paths_returns_the_two_files_copied_to_proc_dir_from_gate_dir(self, mock_get):
        expected = [
            str(pathlib.Path(self.proc_dir) / "test_run_id" / "uri_list_2020-01-01.lst"),
            str(pathlib.Path(self.proc_dir) / "test_run_id" / "uri_list_2020-01-03.lst"),
        ]
        mock_get.side_effect = [
            ['2020-01-01', '2020-01-03'],
            self.gate_dir,
            self.proc_dir,
        ]
        get_uri_list_file_paths(**self.kwargs)
        self.assertListEqual(
            [
                call('old_uri_list_file_paths', []),
                call('new_uri_list_file_paths', expected),
                call('uri_list_file_paths', expected),
            ],
            self.kwargs["ti"].xcom_push.call_args_list
        )

    @patch("check_website.Variable.get")
    def test_get_uri_list_file_paths_returns_all_files_found_in_proc_dir(self, mock_get):
        for f in ("uri_list_2020-03-01.lst", "uri_list_2020-03-02.lst", "uri_list_2020-03-03.lst"):
            file_path = pathlib.Path(self.dag_proc_dir) / f
            with open(file_path, "w") as fp:
                fp.write("")
        expected = [
            str(pathlib.Path(self.dag_proc_dir) / "uri_list_2020-03-01.lst"),
            str(pathlib.Path(self.dag_proc_dir) / "uri_list_2020-03-02.lst"),
            str(pathlib.Path(self.dag_proc_dir) / "uri_list_2020-03-03.lst"),
            str(pathlib.Path(self.dag_proc_dir) / "uri_list_2020-01-01.lst"),
            str(pathlib.Path(self.dag_proc_dir) / "uri_list_2020-01-03.lst"),
        ]
        mock_get.side_effect = [
            ['2020-01-01', '2020-01-03'],
            self.gate_dir,
            self.proc_dir,
        ]
        get_uri_list_file_paths(**self.kwargs)
        self.assertListEqual(
            [
                call('old_uri_list_file_paths', expected[:3]),
                call('new_uri_list_file_paths', expected[-2:]),
                call('uri_list_file_paths', expected),
            ],
            self.kwargs["ti"].xcom_push.call_args_list
        )


class TestGetUriItemsFromUriListFiles(TestCase):

    def setUp(self):
        self.kwargs = {
            "ti": MagicMock(),
            "conf": None,
            "run_id": "test_run_id",
        }
        self.proc_dir = tempfile.mkdtemp()

        content = [
            (
                "/scielo.php?script=sci_serial&pid=0001-3765\n"
                "/scielo.php?script=sci_issues&pid=0001-3765\n"
                "/scielo.php?script=sci_issuetoc&pid=0001-376520200005\n"
                "/scielo.php?script=sci_arttext&pid=S0001-37652020000501101\n"
                ),
            (
                "/scielo.php?script=sci_serial&pid=0001-3035\n"
                "/scielo.php?script=sci_issues&pid=0001-3035\n"
                "/scielo.php?script=sci_issuetoc&pid=0001-303520200005\n"
                "/scielo.php?script=sci_arttext&pid=S0001-30352020000501101\n"
            ),
            (
                "/scielo.php?script=sci_serial&pid=0203-1998\n"
                "/scielo.php?script=sci_issues&pid=0203-1998\n"
                "/scielo.php?script=sci_issuetoc&pid=0203-199820200005\n"
                "/scielo.php?script=sci_arttext&pid=S0203-19982020000501101\n"
                "/scielo.php?script=sci_serial&pid=1213-1998\n"
                "/scielo.php?script=sci_issues&pid=1213-1998\n"
                "/scielo.php?script=sci_issuetoc&pid=1213-199821211115\n"
                "/scielo.php?script=sci_arttext&pid=S1213-19982121111511111\n"
            ),
        ]

        for i, f in enumerate(
                    ["uri_list_2020-01-01.lst",
                     "uri_list_2020-01-02.lst",
                     "uri_list_2020-01-03.lst"]
                ):
            file_path = pathlib.Path(self.proc_dir) / f
            with open(file_path, "w") as fp:
                fp.write(content[i])

    def tearDown(self):
        shutil.rmtree(self.proc_dir)

    def test_get_uri_items_from_uri_list_files_gets_uri_items(self):
        self.kwargs["ti"].xcom_pull.return_value = [
            pathlib.Path(self.proc_dir) / "uri_list_2020-01-01.lst",
            pathlib.Path(self.proc_dir) / "uri_list_2020-01-02.lst",
            pathlib.Path(self.proc_dir) / "uri_list_2020-01-03.lst",

        ]
        get_uri_items_from_uri_list_files(**self.kwargs)
        self.kwargs["ti"].xcom_push.assert_called_once_with(
            "uri_items",
            sorted([
                "/scielo.php?script=sci_serial&pid=0001-3765",
                "/scielo.php?script=sci_issues&pid=0001-3765",
                "/scielo.php?script=sci_issuetoc&pid=0001-376520200005",
                "/scielo.php?script=sci_arttext&pid=S0001-37652020000501101",
                "/scielo.php?script=sci_serial&pid=0001-3035",
                "/scielo.php?script=sci_issues&pid=0001-3035",
                "/scielo.php?script=sci_issuetoc&pid=0001-303520200005",
                "/scielo.php?script=sci_arttext&pid=S0001-30352020000501101",
                "/scielo.php?script=sci_serial&pid=0203-1998",
                "/scielo.php?script=sci_issues&pid=0203-1998",
                "/scielo.php?script=sci_issuetoc&pid=0203-199820200005",
                "/scielo.php?script=sci_arttext&pid=S0203-19982020000501101",
                "/scielo.php?script=sci_serial&pid=1213-1998",
                "/scielo.php?script=sci_issues&pid=1213-1998",
                "/scielo.php?script=sci_issuetoc&pid=1213-199821211115",
                "/scielo.php?script=sci_arttext&pid=S1213-19982121111511111",
            ]),
        )


class TestGetPidListCSVFilePaths(TestCase):

    def setUp(self):
        self.kwargs = {
            "ti": MagicMock(),
            "conf": None,
            "run_id": "test_run_id",
        }
        self.gate_dir = tempfile.mkdtemp()
        self.proc_dir = tempfile.mkdtemp()
        self.dag_proc_dir = str(pathlib.Path(self.proc_dir) / "test_run_id")
        os.makedirs(self.dag_proc_dir)
        for f in ("pid_list_2020-01-01.csv", "pid_list_2020-01-02.csv", "pid_list_2020-01-03.csv"):
            file_path = pathlib.Path(self.gate_dir) / f
            with open(file_path, "w") as fp:
                fp.write("")
        for f in ("any_2020-01-01.lst", "any_2020-01-02.lst", "any_2020-01-03.lst"):
            file_path = pathlib.Path(self.gate_dir) / f
            with open(file_path, "w") as fp:
                fp.write("")
        for f in ("any_2020-01-01.lst", "any_2020-01-02.lst", "any_2020-01-03.lst"):
            file_path = pathlib.Path(self.dag_proc_dir) / f
            with open(file_path, "w") as fp:
                fp.write("")

    def tearDown(self):
        shutil.rmtree(self.gate_dir)
        shutil.rmtree(self.proc_dir)

    @patch("check_website.Variable.get")
    def test_get_pid_list_csv_file_paths_returns_the_two_files_copied_to_proc_dir_from_gate_dir(self, mock_get):
        expected = [
            str(pathlib.Path(self.proc_dir) / "test_run_id" / "pid_list_2020-01-01.csv"),
            str(pathlib.Path(self.proc_dir) / "test_run_id" / "pid_list_2020-01-03.csv"),
        ]
        mock_get.side_effect = [
            ['pid_list_2020-01-01.csv', 'pid_list_2020-01-03.csv'],
            self.gate_dir,
            self.proc_dir,
        ]
        get_pid_list_csv_file_paths(**self.kwargs)
        self.assertListEqual(
            [
                call('old_file_paths', []),
                call('new_file_paths', expected),
                call('file_paths', expected),
            ],
            self.kwargs["ti"].xcom_push.call_args_list
        )

    @patch("check_website.Variable.get")
    def test_get_pid_list_csv_file_paths_returns_all_files_found_in_proc_dir(self, mock_get):
        for f in ("pid_list_2020-03-01.csv", "pid_list_2020-03-02.csv", "pid_list_2020-03-03.csv"):
            file_path = pathlib.Path(self.dag_proc_dir) / f
            with open(file_path, "w") as fp:
                fp.write("")
        expected = [
            str(pathlib.Path(self.dag_proc_dir) / "pid_list_2020-03-01.csv"),
            str(pathlib.Path(self.dag_proc_dir) / "pid_list_2020-03-02.csv"),
            str(pathlib.Path(self.dag_proc_dir) / "pid_list_2020-03-03.csv"),
            str(pathlib.Path(self.dag_proc_dir) / "pid_list_2020-01-01.csv"),
            str(pathlib.Path(self.dag_proc_dir) / "pid_list_2020-01-03.csv"),
        ]
        mock_get.side_effect = [
            ['pid_list_2020-01-01.csv', 'pid_list_2020-01-03.csv'],
            self.gate_dir,
            self.proc_dir,
        ]
        get_pid_list_csv_file_paths(**self.kwargs)
        self.assertListEqual(
            [
                call('old_file_paths', expected[:3]),
                call('new_file_paths', expected[-2:]),
                call('file_paths', expected),
            ],
            self.kwargs["ti"].xcom_push.call_args_list
        )


class TestGetUriItemsFromPidFiles(TestCase):

    def setUp(self):
        self.kwargs = {
            "ti": MagicMock(),
            "conf": None,
            "run_id": "test_run_id",
        }
        self.proc_dir = tempfile.mkdtemp()

        content = [
            (
                "S0001-37652020000501101\n"
                ),
            (
                "S0001-30352020000501101\n"
            ),
            (
                "S0203-19982020000501101\n"
                "S1213-19982121111511111\n"
            ),
        ]

        for i, f in enumerate(
                    ["pid_2020-01-01.csv",
                     "pid_2020-01-02.csv",
                     "pid_2020-01-03.csv"]
                ):
            file_path = pathlib.Path(self.proc_dir) / f
            with open(file_path, "w") as fp:
                fp.write(content[i])

    def tearDown(self):
        shutil.rmtree(self.proc_dir)

    def test_get_uri_items_from_pid_list_csv_files_gets_uri_items(self):
        self.kwargs["ti"].xcom_pull.return_value = [
            pathlib.Path(self.proc_dir) / "pid_2020-01-01.csv",
            pathlib.Path(self.proc_dir) / "pid_2020-01-02.csv",
            pathlib.Path(self.proc_dir) / "pid_2020-01-03.csv",

        ]
        get_uri_items_from_pid_list_csv_files(**self.kwargs)
        self.kwargs["ti"].xcom_push.assert_called_once_with(
            "uri_items",
            [
                "/scielo.php?script=sci_serial&pid=0001-3035",
                "/scielo.php?script=sci_issues&pid=0001-3035",
                "/scielo.php?script=sci_issuetoc&pid=0001-303520200005",
                "/scielo.php?script=sci_arttext&pid=S0001-30352020000501101",
                "/scielo.php?script=sci_pdf&pid=S0001-30352020000501101",
                "/scielo.php?script=sci_serial&pid=0001-3765",
                "/scielo.php?script=sci_issues&pid=0001-3765",
                "/scielo.php?script=sci_issuetoc&pid=0001-376520200005",
                "/scielo.php?script=sci_arttext&pid=S0001-37652020000501101",
                "/scielo.php?script=sci_pdf&pid=S0001-37652020000501101",
                "/scielo.php?script=sci_serial&pid=0203-1998",
                "/scielo.php?script=sci_issues&pid=0203-1998",
                "/scielo.php?script=sci_issuetoc&pid=0203-199820200005",
                "/scielo.php?script=sci_arttext&pid=S0203-19982020000501101",
                "/scielo.php?script=sci_pdf&pid=S0203-19982020000501101",
                "/scielo.php?script=sci_serial&pid=1213-1998",
                "/scielo.php?script=sci_issues&pid=1213-1998",
                "/scielo.php?script=sci_issuetoc&pid=1213-199821211115",
                "/scielo.php?script=sci_arttext&pid=S1213-19982121111511111",
                "/scielo.php?script=sci_pdf&pid=S1213-19982121111511111",
            ],
        )


class TestJoinAndGroupUriItemsByScriptName(TestCase):
    def setUp(self):
        self.kwargs = {
            "ti": MagicMock(),
            "conf": None,
            "run_id": "test_run_id",
        }

    @patch("check_website.Logger.info")
    def test_join_and_group_uri_items_by_script_name(self, mock_info):
        from_uri_list = sorted([
            "/scielo.php?script=sci_serial&pid=0001-3765",
            "/scielo.php?script=sci_issues&pid=0001-3765",
            "/scielo.php?script=sci_issuetoc&pid=0001-376520200005",
            "/scielo.php?script=sci_arttext&pid=S0001-37652020000501101",
            "/scielo.php?script=sci_pdf&pid=S0001-37652020000501101",
            "/scielo.php?script=sci_serial&pid=0001-3035",
            "/scielo.php?script=sci_issues&pid=0001-3035",
            "/scielo.php?script=sci_issuetoc&pid=0001-303520200005",
            "/scielo.php?script=sci_arttext&pid=S0001-30352020000501101",
            "/scielo.php?script=sci_pdf&pid=S0001-30352020000501101",
            "/scielo.php?script=sci_serial&pid=0203-1998",
            "/scielo.php?script=sci_issues&pid=0203-1998",
            "/scielo.php?script=sci_issuetoc&pid=0203-199820200005",
            "/scielo.php?script=sci_arttext&pid=S0203-19982020000501101",
            "/scielo.php?script=sci_pdf&pid=S0203-19982020000501101",
            "/scielo.php?script=sci_serial&pid=1213-1998",
            "/scielo.php?script=sci_issues&pid=1213-1998",
            "/scielo.php?script=sci_issuetoc&pid=1213-199821211115",
            "/scielo.php?script=sci_arttext&pid=S1213-19982121111511111",
            "/scielo.php?script=sci_pdf&pid=S1213-19982121111511111",
        ])
        from_pid_list = [
            "/scielo.php?script=sci_serial&pid=0001-3035",
            "/scielo.php?script=sci_issues&pid=0001-3035",
            "/scielo.php?script=sci_issuetoc&pid=0001-303520200005",
            "/scielo.php?script=sci_arttext&pid=S0001-30352020000501101",
            "/scielo.php?script=sci_pdf&pid=S0001-30352020000501101",
            "/scielo.php?script=sci_serial&pid=0001-3765",
            "/scielo.php?script=sci_issues&pid=0001-3765",
            "/scielo.php?script=sci_issuetoc&pid=0001-376520200005",
            "/scielo.php?script=sci_arttext&pid=S0001-37652020000501101",
            "/scielo.php?script=sci_pdf&pid=S0001-37652020000501101",
            "/scielo.php?script=sci_serial&pid=0203-1998",
            "/scielo.php?script=sci_issues&pid=0203-1998",
            "/scielo.php?script=sci_issuetoc&pid=0203-199820200005",
            "/scielo.php?script=sci_arttext&pid=S0203-19982020000501101",
            "/scielo.php?script=sci_pdf&pid=S0203-19982020000501101",
            "/scielo.php?script=sci_serial&pid=1213-1998",
            "/scielo.php?script=sci_issues&pid=1213-1998",
            "/scielo.php?script=sci_issuetoc&pid=1213-199821211115",
            "/scielo.php?script=sci_arttext&pid=S1213-19982121111511111",
            "/scielo.php?script=sci_arttext&pid=S1213-19982121111511112",
            "/scielo.php?script=sci_arttext&pid=S1213-19982121111511113",
            "/scielo.php?script=sci_arttext&pid=S1213-19982121111511114",
            "/scielo.php?script=sci_pdf&pid=S1213-19982121111511111",
            "/scielo.php?script=sci_pdf&pid=S1213-19982121111511112",
            "/scielo.php?script=sci_pdf&pid=S1213-19982121111511113",
            "/scielo.php?script=sci_pdf&pid=S1213-19982121111511114",
        ]
        self.kwargs["ti"].xcom_pull.side_effect = [
            from_uri_list,
            from_pid_list,
        ]
        join_and_group_uri_items_by_script_name(**self.kwargs)
        self.assertIn(
            call("Total %i URIs", 26),
            mock_info.call_args_list
        )
        self.assertListEqual([
            call(
                'sci_arttext',
                [
                    "/scielo.php?script=sci_arttext&pid=S0001-30352020000501101",
                    "/scielo.php?script=sci_arttext&pid=S0001-37652020000501101",
                    "/scielo.php?script=sci_arttext&pid=S0203-19982020000501101",
                    "/scielo.php?script=sci_arttext&pid=S1213-19982121111511111",
                    "/scielo.php?script=sci_arttext&pid=S1213-19982121111511112",
                    "/scielo.php?script=sci_arttext&pid=S1213-19982121111511113",
                    "/scielo.php?script=sci_arttext&pid=S1213-19982121111511114",
                ]
            ),
            call(
                'sci_pdf',
                [
                    "/scielo.php?script=sci_pdf&pid=S0001-30352020000501101",
                    "/scielo.php?script=sci_pdf&pid=S0001-37652020000501101",
                    "/scielo.php?script=sci_pdf&pid=S0203-19982020000501101",
                    "/scielo.php?script=sci_pdf&pid=S1213-19982121111511111",
                    "/scielo.php?script=sci_pdf&pid=S1213-19982121111511112",
                    "/scielo.php?script=sci_pdf&pid=S1213-19982121111511113",
                    "/scielo.php?script=sci_pdf&pid=S1213-19982121111511114",
                ]
            ),
            call(
                'sci_issuetoc',
                [
                    "/scielo.php?script=sci_issuetoc&pid=0001-303520200005",
                    "/scielo.php?script=sci_issuetoc&pid=0001-376520200005",
                    "/scielo.php?script=sci_issuetoc&pid=0203-199820200005",
                    "/scielo.php?script=sci_issuetoc&pid=1213-199821211115",
                ]
            ),
            call(
                'sci_issues',
                [
                    "/scielo.php?script=sci_issues&pid=0001-3035",
                    "/scielo.php?script=sci_issues&pid=0001-3765",
                    "/scielo.php?script=sci_issues&pid=0203-1998",
                    "/scielo.php?script=sci_issues&pid=1213-1998",
                ]
            ),
            call(
                'sci_serial',
                [
                    "/scielo.php?script=sci_serial&pid=0001-3035",
                    "/scielo.php?script=sci_serial&pid=0001-3765",
                    "/scielo.php?script=sci_serial&pid=0203-1998",
                    "/scielo.php?script=sci_serial&pid=1213-1998",
                ]
            ),
            ],
            self.kwargs["ti"].xcom_push.call_args_list
        )


class TestGetWebsiteURLlist(TestCase):
    @patch("check_website.Variable.get")
    def test_get_website_url_list_raises_value_error_if_variable_WEBSITE_URL_LIST_is_not_set(self, mock_get):
        mock_get.return_value = []
        with self.assertRaises(ValueError):
            get_website_url_list()


class TestCheckSciSerialUriItems(TestCase):
    def setUp(self):
        self.kwargs = {
            "ti": MagicMock(),
            "conf": None,
            "run_id": "test_run_id",
        }

    def test_check_sci_serial_uri_items_assert_called_xcom_pull_with_sci_serial_value(self):
        check_sci_serial_uri_items(**self.kwargs)
        self.kwargs["ti"].xcom_pull.assert_called_once_with(
            task_ids="join_and_group_uri_items_by_script_name_id",
            key="sci_serial"
        )

    @patch("check_website.check_website_operations.concat_website_url_and_uri_list_items")
    @patch("check_website.Variable.get")
    def test_check_sci_serial_uri_items_assert_called_once_concat_website_url_and_uri_list_items(
            self, mock_get, mock_concat_website_url_and_uri_list_items):
        self.kwargs["ti"].xcom_pull.return_value = [
            "/scielo.php?script=sci_serial&pid=0001-3035",
            "/scielo.php?script=sci_serial&pid=0001-3765",
        ]
        mock_get.return_value = ["https://www.scielo.br"]
        check_sci_serial_uri_items(**self.kwargs)
        mock_concat_website_url_and_uri_list_items.assert_called_once_with(
            ["https://www.scielo.br"],
            [
                "/scielo.php?script=sci_serial&pid=0001-3035",
                "/scielo.php?script=sci_serial&pid=0001-3765",
            ]
        )

    @patch("check_website.check_website_operations.check_website_uri_list")
    @patch("check_website.Variable.get")
    def test_check_sci_serial_uri_items_assert_called_once_check_website_uri_list(
            self, mock_get, mock_check_website_uri_list):
        self.kwargs["ti"].xcom_pull.return_value = [
            "/scielo.php?script=sci_serial&pid=0001-3035",
            "/scielo.php?script=sci_serial&pid=0001-3765",
        ]
        mock_get.return_value = ["https://www.scielo.br"]
        check_sci_serial_uri_items(**self.kwargs)
        mock_check_website_uri_list.assert_called_once_with(
            [
                "https://www.scielo.br/scielo.php?script=sci_serial&pid=0001-3035",
                "https://www.scielo.br/scielo.php?script=sci_serial&pid=0001-3765",
            ]
        )


class TestCheckSciIssuesUriItems(TestCase):
    def setUp(self):
        self.kwargs = {
            "ti": MagicMock(),
            "conf": None,
            "run_id": "test_run_id",
        }

    def test_check_sci_issues_uri_items_assert_called_xcom_pull_with_sci_issues_value(self):
        check_sci_issues_uri_items(**self.kwargs)
        self.kwargs["ti"].xcom_pull.assert_called_once_with(
            task_ids="join_and_group_uri_items_by_script_name_id",
            key="sci_issues"
        )

    @patch("check_website.check_website_operations.concat_website_url_and_uri_list_items")
    @patch("check_website.Variable.get")
    def test_check_sci_issues_uri_items_assert_called_once_concat_website_url_and_uri_list_items(
            self, mock_get, mock_concat_website_url_and_uri_list_items):
        self.kwargs["ti"].xcom_pull.return_value = [
            "/scielo.php?script=sci_issues&pid=0001-3035",
            "/scielo.php?script=sci_issues&pid=0001-3765",
        ]
        mock_get.return_value = ["https://www.scielo.br"]
        check_sci_issues_uri_items(**self.kwargs)
        mock_concat_website_url_and_uri_list_items.assert_called_once_with(
            ["https://www.scielo.br"],
            [
                "/scielo.php?script=sci_issues&pid=0001-3035",
                "/scielo.php?script=sci_issues&pid=0001-3765",
            ]
        )

    @patch("check_website.check_website_operations.check_website_uri_list")
    @patch("check_website.Variable.get")
    def test_check_sci_issues_uri_items_assert_called_once_check_website_url_list(
            self, mock_get, mock_check_website_url_list):
        self.kwargs["ti"].xcom_pull.return_value = [
            "/scielo.php?script=sci_issues&pid=0001-3035",
            "/scielo.php?script=sci_issues&pid=0001-3765",
        ]
        mock_get.return_value = ["https://www.scielo.br"]
        check_sci_issues_uri_items(**self.kwargs)
        mock_check_website_url_list.assert_called_once_with(
            [
                "https://www.scielo.br/scielo.php?script=sci_issues&pid=0001-3035",
                "https://www.scielo.br/scielo.php?script=sci_issues&pid=0001-3765",
            ]
        )


class TestCheckSciIssuetocUriItems(TestCase):
    def setUp(self):
        self.kwargs = {
            "ti": MagicMock(),
            "conf": None,
            "run_id": "test_run_id",
        }

    def test_check_sci_issuetoc_uri_items_assert_called_xcom_pull_with_sci_issuetoc_value(self):
        check_sci_issuetoc_uri_items(**self.kwargs)
        self.kwargs["ti"].xcom_pull.assert_called_once_with(
            task_ids="join_and_group_uri_items_by_script_name_id",
            key="sci_issuetoc"
        )

    @patch("check_website.check_website_operations.concat_website_url_and_uri_list_items")
    @patch("check_website.Variable.get")
    def test_check_sci_issuetoc_uri_items_assert_called_once_concat_website_url_and_uri_list_items(
            self, mock_get, mock_concat_website_url_and_uri_list_items):
        self.kwargs["ti"].xcom_pull.return_value = [
            "/scielo.php?script=sci_issuetoc&pid=0001-303520200005",
            "/scielo.php?script=sci_issuetoc&pid=0001-376520200005",
        ]
        mock_get.return_value = ["https://www.scielo.br"]
        check_sci_issuetoc_uri_items(**self.kwargs)
        mock_concat_website_url_and_uri_list_items.assert_called_once_with(
            ["https://www.scielo.br"],
            [
                "/scielo.php?script=sci_issuetoc&pid=0001-303520200005",
                "/scielo.php?script=sci_issuetoc&pid=0001-376520200005",
            ]
        )

    @patch("check_website.check_website_operations.check_website_uri_list")
    @patch("check_website.Variable.get")
    def test_check_sci_issuetoc_uri_items_assert_called_once_check_website_uri_list(
            self, mock_get, mock_check_website_uri_list):
        self.kwargs["ti"].xcom_pull.return_value = [
            "/scielo.php?script=sci_issuetoc&pid=0001-303520200005",
            "/scielo.php?script=sci_issuetoc&pid=0001-376520200005",
        ]
        mock_get.return_value = ["https://www.scielo.br"]
        check_sci_issuetoc_uri_items(**self.kwargs)
        mock_check_website_uri_list.assert_called_once_with(
            [
                "https://www.scielo.br/scielo.php?script=sci_issuetoc&pid=0001-303520200005",
                "https://www.scielo.br/scielo.php?script=sci_issuetoc&pid=0001-376520200005",
            ]
        )


class TestGetPIDv3List(TestCase):
    def setUp(self):
        self.kwargs = {
            "ti": MagicMock(),
            "conf": None,
            "run_id": "test_run_id",
        }

    @patch("check_website.check_website_operations.get_pid_v3_list")
    def test_get_pid_v3_list_assert_called_xcom_pull_with_sci_arttext_value(self, mock_get):
        mock_get.return_value = (
            ["DOCID1", "DOCID2"],
            "https://www.scielo.br"
        )
        get_pid_v3_list(**self.kwargs)
        self.kwargs["ti"].xcom_pull.assert_called_once_with(
            task_ids="join_and_group_uri_items_by_script_name_id",
            key="sci_arttext"
        )

    @patch("check_website.check_website_operations.get_pid_v3_list")
    def test_get_pid_v3_list_assert_called_xcom_push_with_pid_v3_list(self, mock_get):
        mock_get.return_value = (
            ["DOCID1", "DOCID2"],
            "https://www.scielo.br"
        )
        get_pid_v3_list(**self.kwargs)
        self.assertListEqual(
            [
                call("pid_v3_list", ["DOCID1", "DOCID2"]),
                call("website_url", "https://www.scielo.br"),
            ],
            self.kwargs["ti"].xcom_push.call_args_list
        )
