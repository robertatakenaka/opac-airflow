import os
import unittest
from unittest.mock import patch, MagicMock, call
import json

from airflow import DAG

from sync_kernel_to_website import (
    JournalFactory,
    IssueFactory,
    _get_known_documents,
    _get_relation_data,
    _remodel_known_documents,
    _get_relation_data_new,
    _get_relation_data_old,
    pre_register_documents,
    _register_documents,
    _register_documents_renditions,
)
from operations.sync_kernel_to_website_operations import (
    ArticleFactory,
    try_register_documents,
    ArticleRenditionFactory,
    try_register_documents_renditions,
)
from opac_schema.v1 import models
from operations.exceptions import InvalidOrderValueError


FIXTURES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def load_json_fixture(filename):
    with open(os.path.join(FIXTURES_PATH, filename)) as f:
        return json.load(f)


class JournalFactoryTests(unittest.TestCase):
    def setUp(self):
        self.journal_objects = patch("sync_kernel_to_website.models.Journal.objects")
        JournalObjectsMock = self.journal_objects.start()
        JournalObjectsMock.get.side_effect = models.Journal.DoesNotExist
        self.journal_data = load_json_fixture("kernel-journals-1678-4464.json")
        self.journal = JournalFactory(self.journal_data)

    def test_has_method_save(self):
        self.assertTrue(hasattr(self.journal, "save"))

    def test_attribute_mongodb_id(self):
        self.assertEqual(self.journal._id, "1678-4464")

    def test_attribute_jid(self):
        self.assertEqual(self.journal.jid, "1678-4464")

    def test_attribute_title(self):
        self.assertEqual(self.journal.title, "Cadernos de Saúde Pública")

    def test_attribute_title_iso(self):
        self.assertEqual(self.journal.title_iso, "Cad. saúde pública")

    def test_attribute_short_title(self):
        self.assertEqual(self.journal.short_title, "Cad. Saúde Pública")

    def test_attribute_acronym(self):
        self.assertEqual(self.journal.acronym, "csp")

    def test_attribute_scielo_issn(self):
        self.assertEqual(self.journal.scielo_issn, "0102-311X")

    def test_attribute_print_issn(self):
        self.assertEqual(self.journal.print_issn, "0102-311X")

    def test_attribute_eletronic_issn(self):
        self.assertEqual(self.journal.eletronic_issn, "1678-4464")

    def test_attribute_subject_categories(self):
        self.assertEqual(self.journal.subject_categories, ["Health Policy & Services"])

    @unittest.skip("not implemented")
    def test_attribute_metrics(self):
        pass

    def test_attribute_issue_count(self):
        self.assertEqual(self.journal.issue_count, 300)

    @unittest.skip("not implemented")
    def test_attribute_mission(self):
        pass

    def test_attribute_study_areas(self):
        self.assertEqual(self.journal.study_areas, ["HEALTH SCIENCES"])

    def test_attribute_sponsors(self):
        self.assertEqual(
            self.journal.sponsors,
            ["CNPq - Conselho Nacional de Desenvolvimento Científico e Tecnológico "],
        )

    def test_attribute_editor_email(self):
        self.assertEqual(self.journal.editor_email, "cadernos@ensp.fiocruz.br")

    def test_attribute_online_submission_url(self):
        self.assertEqual(
            self.journal.online_submission_url,
            "http://cadernos.ensp.fiocruz.br/csp/index.php",
        )

    def test_attribute_logo_url(self):
        self.assertEqual(
            self.journal.logo_url, "http://cadernos.ensp.fiocruz.br/csp/logo.jpeg"
        )

    def test_attribute_current_status(self):
        self.assertEqual(self.journal.current_status, "current")

    def test_attribute_created(self):
        self.assertEqual(self.journal.created, "1999-07-02T00:00:00.000000Z")

    def test_attribute_updated(self):
        self.assertEqual(self.journal.updated, "2019-07-19T20:33:17.102106Z")


class JournalFactoryExistsInWebsiteTests(unittest.TestCase):
    def setUp(self):
        self.journal_objects = patch(
            "operations.sync_kernel_to_website_operations.models.Journal.objects"
        )
        MockJournal = MagicMock(spec=models.Journal)
        MockJournal.logo_url = "/media/images/glogo.gif"
        JournalObjectsMock = self.journal_objects.start()
        JournalObjectsMock.get.return_value = MockJournal
        self.journal_data = load_json_fixture("kernel-journals-1678-4464.json")
        self.journal = JournalFactory(self.journal_data)

    def test_preserves_logo_if_already_set(self):
        self.assertEqual(self.journal.logo_url, "/media/images/glogo.gif")


class IssueFactoryTests(unittest.TestCase):
    def setUp(self):
        self.mongo_connect_mock = patch(
            "sync_kernel_to_website.mongo_connect"
        )
        self.mongo_connect_mock.start()
        self.journal_objects = patch(
            "sync_kernel_to_website.models.Journal.objects"
        )
        self.MockJournal = MagicMock(spec=models.Journal)
        JournalObjectsMock = self.journal_objects.start()
        JournalObjectsMock.get.return_value = self.MockJournal
        self.issue_objects = patch("sync_kernel_to_website.models.Issue.objects")
        IssueObjectsMock = self.issue_objects.start()
        IssueObjectsMock.get.side_effect = models.Issue.DoesNotExist

        self.issue_data = load_json_fixture("kernel-issues-0001-3714-1998-v29-n3.json")
        self.issue = IssueFactory(self.issue_data, "0001-3714", "12345")

    def tearDown(self):
        self.mongo_connect_mock.stop()
        self.journal_objects.stop()
        self.issue_objects.stop()

    def test_has_method_save(self):
        self.assertTrue(hasattr(self.issue, "save"))

    def test_attribute_mongodb_id(self):
        self.assertEqual(self.issue._id, "0001-3714-1998-v29-n3")

    def test_attribute_journal(self):
        self.assertEqual(self.issue.journal, self.MockJournal)

    def test_attribute_spe_text(self):
        self.assertEqual(self.issue.spe_text, "")

    def test_attribute_start_month(self):
        self.assertEqual(self.issue.start_month, 9)

    def test_attribute_end_month(self):
        self.assertEqual(self.issue.end_month, 9)

    def test_attribute_year(self):
        self.assertEqual(self.issue.year, "1998")

    def test_attribute_number(self):
        self.assertEqual(self.issue.number, "3")

    def test_attribute_volume(self):
        self.assertEqual(self.issue.volume, "29")

    def test_attribute_order(self):
        self.assertEqual(self.issue.order, "12345")

    def test_attribute_pid(self):
        self.assertEqual(self.issue.pid, "0001-371419980003")

    def test_attribute_label(self):
        self.assertEqual(self.issue.label, "v29n3")

    def test_attribute_suppl_text(self):
        self.assertIsNone(self.issue.suppl_text)

    def test_attribute_type(self):
        self.assertEqual(self.issue.type, "regular")

    def test_attribute_created(self):
        self.assertEqual(self.issue.created, "1998-09-01T00:00:00.000000Z")

    def test_attribute_updated(self):
        self.assertEqual(self.issue.updated, "2020-04-28T20:16:24.459467Z")

    def test_attribute_is_public(self):
        self.assertTrue(self.issue.is_public)


class ArticleFactoryTests(unittest.TestCase):
    def setUp(self):
        self.article_objects = patch(
            "operations.sync_kernel_to_website_operations.models.Article.objects"
        )
        self.issue_objects = patch(
            "operations.sync_kernel_to_website_operations.models.Issue.objects"
        )
        ArticleObjectsMock = self.article_objects.start()
        self.issue_objects.start()

        ArticleObjectsMock.get.side_effect = models.Article.DoesNotExist

        self.document_front = load_json_fixture(
            "kernel-document-front-s1518-8787.2019053000621.json"
        )
        self.document = ArticleFactory(
            "67TH7T7CyPPmgtVrGXhWXVs", self.document_front, "issue-1", 621, ""
        )

    def tearDown(self):
        self.article_objects.stop()
        self.issue_objects.stop()

    def test_has_method_save(self):
        self.assertTrue(hasattr(self.document, "save"))

    def test_has_title_attribute(self):
        self.assertTrue(hasattr(self.document, "title"))

    def test_has_section_attribute(self):
        self.assertTrue(hasattr(self.document, "section"))

    def test_has_abstract_attribute(self):
        self.assertTrue(hasattr(self.document, "abstract"))

    def test_has_identification_attributes(self):
        self.assertTrue(hasattr(self.document, "_id"))
        self.assertTrue(hasattr(self.document, "aid"))
        self.assertTrue(hasattr(self.document, "pid"))
        self.assertTrue(hasattr(self.document, "doi"))

        self.assertEqual(self.document._id, "67TH7T7CyPPmgtVrGXhWXVs")
        self.assertEqual(self.document.aid, "67TH7T7CyPPmgtVrGXhWXVs")
        self.assertEqual(self.document.doi, "10.11606/S1518-8787.2019053000621")
        self.assertEqual(self.document.scielo_pids, {
            "v1": "S1518-8787(19)03000621",
            "v2": "S1518-87872019053000621",
            "v3": "67TH7T7CyPPmgtVrGXhWXVs",
        })

    def test_has_authors_attribute(self):
        self.assertTrue(hasattr(self.document, "authors"))

    def test_has_translated_titles_attribute(self):
        self.assertTrue(hasattr(self.document, "translated_titles"))
        self.assertEqual(1, len(self.document.translated_titles))

    def test_has_trans_sections_attribute(self):
        self.assertTrue(hasattr(self.document, "trans_sections"))
        self.assertEqual(2, len(self.document.trans_sections))

    def test_has_abstracts_attribute(self):
        self.assertTrue(hasattr(self.document, "abstracts"))
        self.assertEqual(2, len(self.document.abstracts))

    def test_has_keywords_attribute(self):
        self.assertTrue(hasattr(self.document, "keywords"))
        self.assertEqual(2, len(self.document.keywords))

    def test_has_abstract_languages_attribute(self):
        self.assertTrue(hasattr(self.document, "abstract_languages"))
        self.assertEqual(2, len(self.document.abstract_languages))

    def test_has_original_language_attribute(self):
        self.assertTrue(hasattr(self.document, "original_language"))
        self.assertEqual("en", self.document.original_language)

    def test_has_publication_date_attribute(self):
        self.assertTrue(hasattr(self.document, "publication_date"))
        self.assertEqual("31 01 2019", self.document.publication_date)

    def test_has_type_attribute(self):
        self.assertTrue(hasattr(self.document, "type"))
        self.assertEqual("research-article", self.document.type)

    def test_has_elocation_attribute(self):
        self.assertTrue(hasattr(self.document, "elocation"))

    def test_has_fpage_attribute(self):
        self.assertTrue(hasattr(self.document, "fpage"))

    def test_has_lpage_attribute(self):
        self.assertTrue(hasattr(self.document, "lpage"))

    def test_has_issue_attribute(self):
        self.assertTrue(hasattr(self.document, "issue"))

    def test_has_journal_attribute(self):
        self.assertTrue(hasattr(self.document, "journal"))

    def test_has_order_attribute(self):
        self.assertTrue(hasattr(self.document, "order"))
        self.assertEqual(621, self.document.order)

    def test_has_xml_attribute(self):
        self.assertTrue(hasattr(self.document, "xml"))

    def test_has_htmls_attribute(self):
        self.assertTrue(hasattr(self.document, "htmls"))

    def test_htmls_attibutes_should_be_populated_with_documents_languages(self):
        self.assertEqual([{"lang": "en"}, {"lang": "pt"}], self.document.htmls)

    def test_has_created_attribute(self):
        self.assertTrue(hasattr(self.document, "created"))
        self.assertIsNotNone(self.document.created)

    def test_has_updated_attribute(self):
        self.assertTrue(hasattr(self.document, "updated"))
        self.assertIsNotNone(self.document.updated)

    def test_order_attribute_returns_last_five_digits_of_pid_v2_if_document_order_is_invalid(self):
        for order in ("1bla", None):
            with self.subTest(order=order):
                article = ArticleFactory(
                    document_id="67TH7T7CyPPmgtVrGXhWXVs",
                    data=self.document_front,
                    issue_id="issue-1",
                    document_order=order,
                    document_xml_url=""
                )
                self.assertEqual(621, article.order)

    def test_order_attribute_raise_invalid_order_value_error_because_pid_v2_is_None_and_order_is_alnum(self):
        front = load_json_fixture(
            "kernel-document-front-s1518-8787.2019053000621_sem_pid_v2.json"
        )
        with self.assertRaises(InvalidOrderValueError):
            ArticleFactory(
                document_id="67TH7T7CyPPmgtVrGXhWXVs",
                data=front,
                issue_id="issue-1",
                document_order="bla",
                document_xml_url=""
            )

    def test_order_attribute_returns_zero_because_pid_v2_is_None_and_order_is_None(self):
        front = load_json_fixture(
            "kernel-document-front-s1518-8787.2019053000621_sem_pid_v2.json"
        )
        with self.assertRaises(InvalidOrderValueError):
            ArticleFactory(
                document_id="67TH7T7CyPPmgtVrGXhWXVs",
                data=front,
                issue_id="issue-1",
                document_order=None,
                document_xml_url=""
            )

    def test_order_attribute_returns_order(self):
        front = load_json_fixture(
            "kernel-document-front-s1518-8787.2019053000621_sem_pid_v2.json"
        )
        article = ArticleFactory(
            document_id=MagicMock(),
            data=front,
            issue_id=MagicMock(),
            document_order="1234",
            document_xml_url=MagicMock()
        )
        self.assertEqual(1234, article.order)


@patch("operations.sync_kernel_to_website_operations.models.Article.objects")
@patch("operations.sync_kernel_to_website_operations.models.Issue.objects")
class ExAOPArticleFactoryTests(unittest.TestCase):
    def setUp(self):
        self.document_front = load_json_fixture(
            "kernel-document-front-s1518-8787.2019053000621.json"
        )
        data = {
            "id": "0101-0101",
            "created": "2019-11-28T00:00:00.000000Z",
            "metadata": {},
        }
        self.issue = models.Issue()
        self.issue._id = "0101-0101-aop"
        self.issue.year = "2019"
        self.issue.number = "ahead"
        self.issue.url_segment = "2019.nahead"

    def test_sets_aop_url_segs(self, MockIssueObjects, MockArticleObjects):
        MockArticle = MagicMock(
            spec=models.Article,
            aop_url_segs=None,
            url_segment="10.151/S1518-8787.2019053000621"
        )
        MockArticle.issue = self.issue
        MockArticleObjects.get.return_value = MockArticle
        self.document = ArticleFactory(
            "67TH7T7CyPPmgtVrGXhWXVs", self.document_front, "issue-1", "1", ""
        )
        self.assertIsNotNone(self.document.aop_url_segs)
        self.assertIsInstance(self.document.aop_url_segs, models.AOPUrlSegments)
        self.assertEqual(
            self.document.aop_url_segs.url_seg_article,
            "10.151/S1518-8787.2019053000621"
        )
        self.assertEqual(
            self.document.aop_url_segs.url_seg_issue,
            "2019.nahead"
        )


class RegisterDocumentTests(unittest.TestCase):
    def setUp(self):
        self.documents = ["67TH7T7CyPPmgtVrGXhWXVs"]
        self.document_front = load_json_fixture(
            "kernel-document-front-s1518-8787.2019053000621.json"
        )

        mk_hooks = patch("operations.sync_kernel_to_website_operations.hooks")
        self.mk_hooks = mk_hooks.start()

    def tearDown(self):
        self.mk_hooks.stop()

    def test_try_register_documents_call_save_methods_from_article_instance(self):
        article_factory_mock = MagicMock()
        article_instance_mock = MagicMock()
        article_factory_mock.return_value = article_instance_mock

        try_register_documents(
            documents=self.documents,
            get_relation_data=lambda document_id: (
                "issue-1",
                {"id": "67TH7T7CyPPmgtVrGXhWXVs", "order": "01"},
            ),
            fetch_document_front=lambda document_id: self.document_front,
            article_factory=article_factory_mock,
        )

        article_instance_mock.save.assert_called_once()

    def test_try_register_documents_call_fetch_document_front_once(self):
        fetch_document_front_mock = MagicMock()
        article_factory_mock = MagicMock()

        try_register_documents(
            documents=self.documents,
            get_relation_data=lambda _: ("", {}),
            fetch_document_front=fetch_document_front_mock,
            article_factory=article_factory_mock,
        )

        fetch_document_front_mock.assert_called_once_with("67TH7T7CyPPmgtVrGXhWXVs")

    def test_try_register_documents_call_article_factory_once(self):
        article_factory_mock = MagicMock()
        self.mk_hooks.KERNEL_HOOK_BASE.run.side_effect = [
            MagicMock(url="http://kernel_url/")
        ]

        try_register_documents(
            documents=self.documents,
            get_relation_data=lambda _: (
                "issue-1",
                {"id": "67TH7T7CyPPmgtVrGXhWXVs", "order": "01"},
            ),
            fetch_document_front=lambda _: self.document_front,
            article_factory=article_factory_mock,
        )

        article_factory_mock.assert_called_once_with(
            "67TH7T7CyPPmgtVrGXhWXVs",
            self.document_front,
            "issue-1",
            "01",
            "http://kernel_url/documents/67TH7T7CyPPmgtVrGXhWXVs",
        )

class ArticleRenditionFactoryTests(unittest.TestCase):
    def setUp(self):
        self.article_objects = patch(
            "operations.sync_kernel_to_website_operations.models.Article.objects"
        )

        ArticleObjectsMock = self.article_objects.start()
        ArticleObjectsMock.get.side_effect = MagicMock()

        self.document_front = load_json_fixture(
            "kernel-document-front-s1518-8787.2019053000621.json"
        )
        self.article = ArticleRenditionFactory(
            "67TH7T7CyPPmgtVrGXhWXVs",
            [
                {
                    "filename": "filename.pdf",
                    "url": "//object-storage/file.pdf",
                    "mimetype": "application/pdf",
                    "lang": "en",
                    "size_bytes": 1,
                }
            ],
        )

    def tearDown(self):
        self.article_objects.stop()

    def test_pdfs_attr_should_be_populated_with_rendition_pdf_data(self):
        self.assertEqual(
            [
                {
                    "lang": "en",
                    "url": "//object-storage/file.pdf",
                    "type": "pdf",
                    "filename": "filename.pdf",
                }
            ],
            self.article.pdfs,
        )


class RegisterDocumentRenditionsTest(unittest.TestCase):
    def setUp(self):
        self.documents = ["67TH7T7CyPPmgtVrGXhWXVs"]
        self.document_front = load_json_fixture(
            "kernel-document-front-s1518-8787.2019053000621.json"
        )

        mk_hooks = patch("operations.sync_kernel_to_website_operations.hooks")
        self.mk_hooks = mk_hooks.start()

        self.renditions = [
            {
                "filename": "filename.pdf",
                "url": "//object-storage/file.pdf",
                "mimetype": "application/pdf",
                "lang": "en",
                "size_bytes": 1,
            }
        ]

    def tearDown(self):
        self.mk_hooks.stop()

    def test_try_register_documents_renditions_call_save_methods_from_article_instance(
        self
    ):
        article_rendition_factory_mock = MagicMock()
        article_instance_mock = MagicMock()
        article_rendition_factory_mock.return_value = article_instance_mock

        orphans = try_register_documents_renditions(
            documents=self.documents,
            get_rendition_data=lambda document_id: self.renditions,
            article_rendition_factory=article_rendition_factory_mock,
        )

        article_instance_mock.save.assert_called()

        self.assertEqual([], orphans)

    def test_has_orphans_when_try_register_an_orphan_rendition(self):
        article_rendition_factory_mock = MagicMock()
        article_rendition_factory_mock.side_effect = [models.Article.DoesNotExist]

        orphans = try_register_documents_renditions(
            documents=self.documents,
            get_rendition_data=lambda document_id: self.renditions,
            article_rendition_factory=article_rendition_factory_mock,
        )

        self.assertEqual(self.documents, orphans)


@patch("sync_kernel_to_website.filter_changes")
@patch("sync_kernel_to_website.fetch_bundles")
class TestGetKnownDocuments(unittest.TestCase):

    def test__get_known_documents_adds_and_returns_new_issue_and_its_documents_in_input_dict(
            self, mock_fetch_bundles, mock_filter_changes):
        mock_issue = {
            "_id": "0001-3714-1999-v60-n2",
            "id": "0001-3714-1999-v60-n2",
            "created": "2020-10-06T15:15:04.310621Z",
            "updated": "2020-10-06T15:15:04.311271Z",
            "items": [
                {"id": "9CgFRVMHSKmp6Msj5CPBZRb", "order": "00502"},
                {"id": "c4H4TjsZS7YzjTjyYD5f5Ct", "order": "00501"},
                {"id": "QXJwLFnG565Prww5YdqqpTq", "order": "00504"},
            ],
            "metadata": {
                "publication_months": {"range": [9, 10]},
                "publication_year": "2020",
                "volume": "67",
                "number": "5",
                "pid": "0034-737X20200005"
            }
        }
        mock_fetch_bundles.side_effect = [mock_issue]
        mock_filter_changes.return_value = [
            {
                "id": "/bundles/0001-3714-1999-v60-n2",
                "timestamp": "2020-11-05T16:54:12.236462Z",
                "change_id": "5fa42e34c1e393cec121d6b5"

            },
        ]
        tasks = MagicMock()
        known_documents = {
            "0001-3714-1998-v29-n3": [],
        }
        expected = {
            "0001-3714-1998-v29-n3": [],
            "0001-3714-1999-v60-n2": [
                {"id": "9CgFRVMHSKmp6Msj5CPBZRb", "order": "00502"},
                {"id": "c4H4TjsZS7YzjTjyYD5f5Ct", "order": "00501"},
                {"id": "QXJwLFnG565Prww5YdqqpTq", "order": "00504"},
            ],
        }

        result = _get_known_documents(known_documents, tasks)
        self.assertDictEqual(expected, result)
        self.assertIs(known_documents, result)

    def test__get_known_documents_adds_and_returns_new_issue_and_no_documents_in_input_dict(
            self, mock_fetch_bundles, mock_filter_changes):
        mock_issue = {}
        mock_fetch_bundles.side_effect = [mock_issue]
        mock_filter_changes.return_value = [
            {
                "id": "/bundles/0001-3714-1999-v60-n2",
                "timestamp": "2020-11-05T16:54:12.236462Z",
                "change_id": "5fa42e34c1e393cec121d6b5"

            },
        ]
        tasks = MagicMock()
        known_documents = {
            "0001-3714-1998-v29-n3": [],
        }
        expected = {
            "0001-3714-1998-v29-n3": [],
            "0001-3714-1999-v60-n2": [],
        }

        result = _get_known_documents(known_documents, tasks)
        self.assertDictEqual(expected, result)

    def test__get_known_documents_returns_unchanged_input_dict(
            self, mock_fetch_bundles, mock_filter_changes):
        mock_filter_changes.return_value = []
        tasks = MagicMock()
        known_documents = {
            "0001-3714-1998-v29-n3": [],
        }
        expected = known_documents.copy()

        result = _get_known_documents(known_documents, tasks)
        self.assertDictEqual(expected, result)

    def test__get_known_documents_do_nothing_because_input_dict_has_already_documents(
            self, mock_fetch_bundles, mock_filter_changes):
        mock_issue = {
            "_id": "0001-3714-1999-v60-n2",
            "id": "0001-3714-1999-v60-n2",
            "created": "2020-10-06T15:15:04.310621Z",
            "updated": "2020-10-06T15:15:04.311271Z",
            "items": [
                {"id": "9CgFRVMHSKmp6Msj5CPBZRb", "order": "00502"},
                {"id": "c4H4TjsZS7YzjTjyYD5f5Ct", "order": "00501"},
                {"id": "QXJwLFnG565Prww5YdqqpTq", "order": "00504"},
            ],
            "metadata": {
                "publication_months": {"range": [9, 10]},
                "publication_year": "2020",
                "volume": "67",
                "number": "5",
                "pid": "0034-737X20200005"
            }
        }
        mock_fetch_bundles.side_effect = [mock_issue]
        mock_filter_changes.return_value = [
            {
                "id": "/bundles/0001-3714-1999-v60-n2",
                "timestamp": "2020-11-05T16:54:12.236462Z",
                "change_id": "5fa42e34c1e393cec121d6b5"

            },
        ]
        tasks = MagicMock()
        known_documents = {
            "0001-3714-1999-v60-n2": [
                {"id": "RCgFV9MHSKmp6Msj5CPBZRb", "order": "00602"},
            ],
        }
        expected = known_documents.copy()

        result = _get_known_documents(known_documents, tasks)
        self.assertDictEqual(expected, result)
        self.assertIs(known_documents, result)


class TestGetRelationData(unittest.TestCase):

    def test__get_relation_data_returns_bundle_and_document(self):
        known_documents = {
            "issue_id": [
                {"id": "RCgFV9MHSKmp6Msj5CPBZRb", "order": "00602"},
                {"id": "CGgFV9MHSKmp6Msj5CPBZRb", "order": "00604"},
                {"id": "HJgFV9MHSKmp6Msj5CPBZRb", "order": "00607"},
                {"id": "LLgFV9MHSKmp6Msj5CPBZRb", "order": "00609"},
            ],
            "issue_id_2": [
                {"id": "RC13V9MHSKmp6Msj5CPBZRb", "order": "00602"},
                {"id": "CG13V9MHSKmp6Msj5CPBZRb", "order": "00604"},
                {"id": "HJ13V9MHSKmp6Msj5CPBZRb", "order": "00607"},
                {"id": "LL13V9MHSKmp6Msj5CPBZRb", "order": "00609"},
            ]
        }
        document_id = "HJgFV9MHSKmp6Msj5CPBZRb"
        expected = (
            "issue_id",
            {"id": "HJgFV9MHSKmp6Msj5CPBZRb", "order": "00607"}
        )
        result = _get_relation_data(known_documents, document_id)
        self.assertEqual(expected, result)

    def test__get_relation_data_returns_none_and_no_docs(self):
        known_documents = {
            "issue_id": [
                {"id": "RCgFV9MHSKmp6Msj5CPBZRb", "order": "00602"},
                {"id": "CGgFV9MHSKmp6Msj5CPBZRb", "order": "00604"},
                {"id": "HJgFV9MHSKmp6Msj5CPBZRb", "order": "00607"},
                {"id": "LLgFV9MHSKmp6Msj5CPBZRb", "order": "00609"},
            ],
            "issue_id_2": [
                {"id": "RC13V9MHSKmp6Msj5CPBZRb", "order": "00602"},
                {"id": "CG13V9MHSKmp6Msj5CPBZRb", "order": "00604"},
                {"id": "HJ13V9MHSKmp6Msj5CPBZRb", "order": "00607"},
                {"id": "LL13V9MHSKmp6Msj5CPBZRb", "order": "00609"},
            ]
        }
        document_id = "AAAAAAMHSKmp6Msj5CPBZRb"
        expected = (None, {})
        result = _get_relation_data(known_documents, document_id)
        self.assertEqual(expected, result)

    def test__get_relation_data_uses_remodeled_known_documents_and_returns_bundle_and_document(self):
        known_documents = {
            "RCgFV9MHSKmp6Msj5CPBZRb": (
                "issue_id",
                {"id": "RCgFV9MHSKmp6Msj5CPBZRb", "order": "00602"},
            ),
            "CGgFV9MHSKmp6Msj5CPBZRb": (
                "issue_id",
                {"id": "CGgFV9MHSKmp6Msj5CPBZRb", "order": "00604"},
            ),
            "HJgFV9MHSKmp6Msj5CPBZRb": (
                "issue_id",
                {"id": "HJgFV9MHSKmp6Msj5CPBZRb", "order": "00607"},
            ),
            "LLgFV9MHSKmp6Msj5CPBZRb": (
                "issue_id",
                {"id": "LLgFV9MHSKmp6Msj5CPBZRb", "order": "00609"},
            ),
            "RC13V9MHSKmp6Msj5CPBZRb": (
                "issue_id_2",
                {"id": "RC13V9MHSKmp6Msj5CPBZRb", "order": "00602"},
            ),
            "CG13V9MHSKmp6Msj5CPBZRb": (
                "issue_id_2",
                {"id": "CG13V9MHSKmp6Msj5CPBZRb", "order": "00604"},
            ),
            "HJ13V9MHSKmp6Msj5CPBZRb": (
                "issue_id_2",
                {"id": "HJ13V9MHSKmp6Msj5CPBZRb", "order": "00607"},
            ),
            "LL13V9MHSKmp6Msj5CPBZRb": (
                "issue_id_2",
                {"id": "LL13V9MHSKmp6Msj5CPBZRb", "order": "00609"},
            ),
        }
        document_id = "HJgFV9MHSKmp6Msj5CPBZRb"
        expected = (
            "issue_id",
            {"id": "HJgFV9MHSKmp6Msj5CPBZRb", "order": "00607"}
        )
        result = _get_relation_data(known_documents, document_id)
        self.assertEqual(expected, result)

    def test__get_relation_data_uses_remodeled_known_documents_and_returns_none_and_no_docs(self):
        known_documents = {
            "RCgFV9MHSKmp6Msj5CPBZRb": (
                "issue_id",
                {"id": "RCgFV9MHSKmp6Msj5CPBZRb", "order": "00602"},
            ),
            "CGgFV9MHSKmp6Msj5CPBZRb": (
                "issue_id",
                {"id": "CGgFV9MHSKmp6Msj5CPBZRb", "order": "00604"},
            ),
            "HJgFV9MHSKmp6Msj5CPBZRb": (
                "issue_id",
                {"id": "HJgFV9MHSKmp6Msj5CPBZRb", "order": "00607"},
            ),
            "LLgFV9MHSKmp6Msj5CPBZRb": (
                "issue_id",
                {"id": "LLgFV9MHSKmp6Msj5CPBZRb", "order": "00609"},
            ),
            "RC13V9MHSKmp6Msj5CPBZRb": (
                "issue_id_2",
                {"id": "RC13V9MHSKmp6Msj5CPBZRb", "order": "00602"},
            ),
            "CG13V9MHSKmp6Msj5CPBZRb": (
                "issue_id_2",
                {"id": "CG13V9MHSKmp6Msj5CPBZRb", "order": "00604"},
            ),
            "HJ13V9MHSKmp6Msj5CPBZRb": (
                "issue_id_2",
                {"id": "HJ13V9MHSKmp6Msj5CPBZRb", "order": "00607"},
            ),
            "LL13V9MHSKmp6Msj5CPBZRb": (
                "issue_id_2",
                {"id": "LL13V9MHSKmp6Msj5CPBZRb", "order": "00609"},
            ),
        }
        document_id = "AAAAAAMHSKmp6Msj5CPBZRb"
        expected = (None, {})
        result = _get_relation_data(known_documents, document_id)
        self.assertEqual(expected, result)


class TestGetRelationDataNew(unittest.TestCase):

    def test__get_relation_data_new_returns_None(self):
        known_documents = {
            "issue_id": [
                {"id": "RCgFV9MHSKmp6Msj5CPBZRb", "order": "00602"},
                {"id": "CGgFV9MHSKmp6Msj5CPBZRb", "order": "00604"},
                {"id": "HJgFV9MHSKmp6Msj5CPBZRb", "order": "00607"},
                {"id": "LLgFV9MHSKmp6Msj5CPBZRb", "order": "00609"},
            ],
            "issue_id_2": [
                {"id": "RC13V9MHSKmp6Msj5CPBZRb", "order": "00602"},
                {"id": "CG13V9MHSKmp6Msj5CPBZRb", "order": "00604"},
                {"id": "HJ13V9MHSKmp6Msj5CPBZRb", "order": "00607"},
                {"id": "LL13V9MHSKmp6Msj5CPBZRb", "order": "00609"},
            ]
        }
        document_id = "HJgFV9MHSKmp6Msj5CPBZRb"
        expected = None
        result = _get_relation_data_new(known_documents, document_id)
        self.assertEqual(expected, result)

    def test__get_relation_data_new_returns_none_and_no_docs(self):
        known_documents = {}
        document_id = "AAAAAAMHSKmp6Msj5CPBZRb"
        expected = (None, {})
        result = _get_relation_data_new(known_documents, document_id)
        self.assertEqual(expected, result)

    def test__get_relation_data_new_returns_bundle_and_document(self):
        known_documents = {
            "RCgFV9MHSKmp6Msj5CPBZRb": (
                "issue_id",
                {"id": "RCgFV9MHSKmp6Msj5CPBZRb", "order": "00602"},
            ),
            "CGgFV9MHSKmp6Msj5CPBZRb": (
                "issue_id",
                {"id": "CGgFV9MHSKmp6Msj5CPBZRb", "order": "00604"},
            ),
            "HJgFV9MHSKmp6Msj5CPBZRb": (
                "issue_id",
                {"id": "HJgFV9MHSKmp6Msj5CPBZRb", "order": "00607"},
            ),
            "LLgFV9MHSKmp6Msj5CPBZRb": (
                "issue_id",
                {"id": "LLgFV9MHSKmp6Msj5CPBZRb", "order": "00609"},
            ),
            "RC13V9MHSKmp6Msj5CPBZRb": (
                "issue_id_2",
                {"id": "RC13V9MHSKmp6Msj5CPBZRb", "order": "00602"},
            ),
            "CG13V9MHSKmp6Msj5CPBZRb": (
                "issue_id_2",
                {"id": "CG13V9MHSKmp6Msj5CPBZRb", "order": "00604"},
            ),
            "HJ13V9MHSKmp6Msj5CPBZRb": (
                "issue_id_2",
                {"id": "HJ13V9MHSKmp6Msj5CPBZRb", "order": "00607"},
            ),
            "LL13V9MHSKmp6Msj5CPBZRb": (
                "issue_id_2",
                {"id": "LL13V9MHSKmp6Msj5CPBZRb", "order": "00609"},
            ),
        }
        document_id = "HJgFV9MHSKmp6Msj5CPBZRb"
        expected = (
            "issue_id",
            {"id": "HJgFV9MHSKmp6Msj5CPBZRb", "order": "00607"}
        )
        result = _get_relation_data_new(known_documents, document_id)
        self.assertEqual(expected, result)

    @patch("sync_kernel_to_website.isinstance")
    def test__get_relation_data_new_calls_isinstance_once(self, mock_isinstance):
        known_documents = {
            "RCgFV9MHSKmp6Msj5CPBZRb": (
                "issue_id",
                {"id": "RCgFV9MHSKmp6Msj5CPBZRb", "order": "00602"},
            ),
            "CGgFV9MHSKmp6Msj5CPBZRb": (
                "issue_id",
                {"id": "CGgFV9MHSKmp6Msj5CPBZRb", "order": "00604"},
            ),
            "HJgFV9MHSKmp6Msj5CPBZRb": (
                "issue_id",
                {"id": "HJgFV9MHSKmp6Msj5CPBZRb", "order": "00607"},
            ),
            "LLgFV9MHSKmp6Msj5CPBZRb": (
                "issue_id",
                {"id": "LLgFV9MHSKmp6Msj5CPBZRb", "order": "00609"},
            ),
            "RC13V9MHSKmp6Msj5CPBZRb": (
                "issue_id_2",
                {"id": "RC13V9MHSKmp6Msj5CPBZRb", "order": "00602"},
            ),
            "CG13V9MHSKmp6Msj5CPBZRb": (
                "issue_id_2",
                {"id": "CG13V9MHSKmp6Msj5CPBZRb", "order": "00604"},
            ),
            "HJ13V9MHSKmp6Msj5CPBZRb": (
                "issue_id_2",
                {"id": "HJ13V9MHSKmp6Msj5CPBZRb", "order": "00607"},
            ),
            "LL13V9MHSKmp6Msj5CPBZRb": (
                "issue_id_2",
                {"id": "LL13V9MHSKmp6Msj5CPBZRb", "order": "00609"},
            ),
        }
        document_id = "AAAAAAMHSKmp6Msj5CPBZRb"
        expected = (None, {})
        result = _get_relation_data_new(known_documents, document_id)
        self.assertEqual(expected, result)
        mock_isinstance.assert_called_once()


class TestGetRelationDataOld(unittest.TestCase):

    def test__get_relation_data_old_returns_bundle_and_document(self):
        known_documents = {
            "issue_id": [
                {"id": "RCgFV9MHSKmp6Msj5CPBZRb", "order": "00602"},
                {"id": "CGgFV9MHSKmp6Msj5CPBZRb", "order": "00604"},
                {"id": "HJgFV9MHSKmp6Msj5CPBZRb", "order": "00607"},
                {"id": "LLgFV9MHSKmp6Msj5CPBZRb", "order": "00609"},
            ],
            "issue_id_2": [
                {"id": "RC13V9MHSKmp6Msj5CPBZRb", "order": "00602"},
                {"id": "CG13V9MHSKmp6Msj5CPBZRb", "order": "00604"},
                {"id": "HJ13V9MHSKmp6Msj5CPBZRb", "order": "00607"},
                {"id": "LL13V9MHSKmp6Msj5CPBZRb", "order": "00609"},
            ]
        }
        document_id = "HJgFV9MHSKmp6Msj5CPBZRb"
        expected = (
            "issue_id",
            {"id": "HJgFV9MHSKmp6Msj5CPBZRb", "order": "00607"}
        )
        result = _get_relation_data_old(known_documents, document_id)
        self.assertEqual(expected, result)

    def test__get_relation_data_old_returns_none_and_no_docs(self):
        known_documents = {
            "issue_id": [
                {"id": "RCgFV9MHSKmp6Msj5CPBZRb", "order": "00602"},
                {"id": "CGgFV9MHSKmp6Msj5CPBZRb", "order": "00604"},
                {"id": "HJgFV9MHSKmp6Msj5CPBZRb", "order": "00607"},
                {"id": "LLgFV9MHSKmp6Msj5CPBZRb", "order": "00609"},
            ],
            "issue_id_2": [
                {"id": "RC13V9MHSKmp6Msj5CPBZRb", "order": "00602"},
                {"id": "CG13V9MHSKmp6Msj5CPBZRb", "order": "00604"},
                {"id": "HJ13V9MHSKmp6Msj5CPBZRb", "order": "00607"},
                {"id": "LL13V9MHSKmp6Msj5CPBZRb", "order": "00609"},
            ]
        }
        document_id = "AAAAAAMHSKmp6Msj5CPBZRb"
        expected = (None, {})
        result = _get_relation_data_old(known_documents, document_id)
        self.assertEqual(expected, result)


class TestRemodelKnownDocuments(unittest.TestCase):

    def test__remodel_known_documents(self):
        known_documents = {
            "issue_id": [
                {"id": "RCgFV9MHSKmp6Msj5CPBZRb", "order": "00602"},
                {"id": "CGgFV9MHSKmp6Msj5CPBZRb", "order": "00604"},
                {"id": "HJgFV9MHSKmp6Msj5CPBZRb", "order": "00607"},
                {"id": "LLgFV9MHSKmp6Msj5CPBZRb", "order": "00609"},
            ],
            "issue_id_2": [
                {"id": "RC13V9MHSKmp6Msj5CPBZRb", "order": "00602"},
                {"id": "CG13V9MHSKmp6Msj5CPBZRb", "order": "00604"},
                {"id": "HJ13V9MHSKmp6Msj5CPBZRb", "order": "00607"},
                {"id": "LL13V9MHSKmp6Msj5CPBZRb", "order": "00609"},
            ]
        }
        expected = {
            "RCgFV9MHSKmp6Msj5CPBZRb": (
                "issue_id",
                {"id": "RCgFV9MHSKmp6Msj5CPBZRb", "order": "00602"},
            ),
            "CGgFV9MHSKmp6Msj5CPBZRb": (
                "issue_id",
                {"id": "CGgFV9MHSKmp6Msj5CPBZRb", "order": "00604"},
            ),
            "HJgFV9MHSKmp6Msj5CPBZRb": (
                "issue_id",
                {"id": "HJgFV9MHSKmp6Msj5CPBZRb", "order": "00607"},
            ),
            "LLgFV9MHSKmp6Msj5CPBZRb": (
                "issue_id",
                {"id": "LLgFV9MHSKmp6Msj5CPBZRb", "order": "00609"},
            ),
            "RC13V9MHSKmp6Msj5CPBZRb": (
                "issue_id_2",
                {"id": "RC13V9MHSKmp6Msj5CPBZRb", "order": "00602"},
            ),
            "CG13V9MHSKmp6Msj5CPBZRb": (
                "issue_id_2",
                {"id": "CG13V9MHSKmp6Msj5CPBZRb", "order": "00604"},
            ),
            "HJ13V9MHSKmp6Msj5CPBZRb": (
                "issue_id_2",
                {"id": "HJ13V9MHSKmp6Msj5CPBZRb", "order": "00607"},
            ),
            "LL13V9MHSKmp6Msj5CPBZRb": (
                "issue_id_2",
                {"id": "LL13V9MHSKmp6Msj5CPBZRb", "order": "00609"},
            ),
        }
        result = _remodel_known_documents(known_documents)
        self.assertEqual(expected, result)


@patch("sync_kernel_to_website.Variable.set")
class TestPreRegisterDocuments(unittest.TestCase):

    def setUp(self):
        self.kwargs = {
            "ti": MagicMock(),
            "conf": None,
            "run_id": "test_run_id",
        }

    def test_pre_register_documents_gets_data_from_xcom_and_set_vars(
            self, mock_set):
        mock_tasks = [
            {"id": "/documents/QTsr9VQHDd4DL5zqWqkwyjk",
             "task": "get"},
            {"id": "/documents/QTsr9VQHDd4DL5zqWqkwyjk/renditions",
             "task": "get"},
            {"id": "/bundles/2236-9996-2020-v22-n47",
             "task": "get"},
            {"id": "/documents/S0104-42302020000500589",
             "task": "get"},
            {"id": "/documents/S0104-42302020000500589/renditions",
             "task": "get"},
        ]
        mock_i_docs = {
            "2236-9996-2020-v22-n47":
                [{"id": "QTsr9VQHDd4DL5zqWqkwyjk", "order": "00017"}],
            "0034-8910-1974-v8-s0": [],
            "0034-8910-1976-v10-s1": [],
        }
        self.kwargs["ti"].xcom_pull.side_effect = [
            mock_tasks,
            mock_i_docs,
        ]
        pre_register_documents(**self.kwargs)
        calls = [
            call("read_changes_task__tasks", mock_tasks, serialize_json=True),
            call("register_issues_task__i_documents",
                 mock_i_docs, serialize_json=True),
        ]
        self.assertListEqual(calls, mock_set.call_args_list)


@patch("sync_kernel_to_website.fetch_documents_front")
@patch("sync_kernel_to_website.Variable.set")
@patch("sync_kernel_to_website.Variable.get")
@patch("sync_kernel_to_website.try_register_documents")
@patch("sync_kernel_to_website.mongo_connect")
class TestRegisterDocuments(unittest.TestCase):

    def setUp(self):
        self.kwargs = {
            "ti": MagicMock(),
            "conf": None,
            "run_id": "test_run_id",
        }

    def test__register_documents(self, mock_mongo, mock_try_reg, mock_get,
            mock_set, mock_fetch):
        documents_to_get = [
            "QTsr9VQHDd4DL5zqWqkwyjk", "LL13V9MHSKmp6Msj5CPBZRb"]
        _get_relation_data = MagicMock(spec=callable)

        mock_try_reg.return_value = ["LL13V9MHSKmp6Msj5CPBZRb"]
        mock_get.return_value = ["6Msj5CPBZRbLL13V9MHSKmp"]

        _register_documents(
            documents_to_get, _get_relation_data, **self.kwargs)

        mock_try_reg.assert_called_once_with(
            documents_to_get, _get_relation_data,
            mock_fetch, ArticleFactory
        )
        mock_get.assert_called_once_with(
            "orphan_documents", [], deserialize_json=True
        )
        mock_set.assert_called_once_with(
            "orphan_documents",
            ["6Msj5CPBZRbLL13V9MHSKmp", "LL13V9MHSKmp6Msj5CPBZRb"],
            serialize_json=True
        )


@patch("sync_kernel_to_website.fetch_documents_renditions")
@patch("sync_kernel_to_website.Variable.set")
@patch("sync_kernel_to_website.Variable.get")
@patch("sync_kernel_to_website.try_register_documents_renditions")
@patch("sync_kernel_to_website.mongo_connect")
class TestRegisterDocumentsRenditions(unittest.TestCase):

    def setUp(self):
        self.kwargs = {
            "ti": MagicMock(),
            "conf": None,
            "run_id": "test_run_id",
        }

    def test__register_documents_renditions(self, mock_mongo, mock_try_reg,
            mock_get,
            mock_set, mock_fetch):
        documents_to_get = [
            "QTsr9VQHDd4DL5zqWqkwyjk", "LL13V9MHSKmp6Msj5CPBZRb"]
        _get_relation_data = MagicMock(spec=callable)

        mock_try_reg.return_value = ["LL13V9MHSKmp6Msj5CPBZRb"]
        mock_get.return_value = ["6Msj5CPBZRbLL13V9MHSKmp"]

        _register_documents_renditions(
            documents_to_get, **self.kwargs)

        mock_try_reg.assert_called_once_with(
            documents_to_get,
            mock_fetch, ArticleRenditionFactory
        )
        mock_get.assert_called_once_with(
            "orphan_renditions", [], deserialize_json=True
        )
        mock_set.assert_called_once_with(
            "orphan_renditions",
            ["6Msj5CPBZRbLL13V9MHSKmp", "LL13V9MHSKmp6Msj5CPBZRb"],
            serialize_json=True
        )