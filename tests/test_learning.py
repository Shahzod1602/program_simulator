import json
from pathlib import Path
import unittest

import test_runner as base

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / 'public' / 'learning-data.json').read_text())


class CurriculumTests(unittest.TestCase):
    def test_all_languages_have_complete_learning_paths(self):
        self.assertEqual(len(DATA['lessons']), 32)
        self.assertEqual(len(DATA['examples']), 40)
        self.assertEqual(len(DATA['references']), 32)
        self.assertEqual(len(DATA['algorithms']), 8)
        for language in DATA['languages']:
            lessons = [item for item in DATA['lessons'] if item['language'] == language]
            self.assertEqual([item['order'] for item in lessons], [1, 2, 3, 4])
            self.assertGreaterEqual(len([item for item in DATA['examples'] if item['language'] == language]), 5)
            self.assertEqual(len([item for item in DATA['references'] if item['language'] == language]), 4)

    def test_content_integrity_and_quizzes(self):
        for section in ('lessons', 'examples', 'references', 'algorithms'):
            ids = [item['id'] for item in DATA[section]]
            self.assertEqual(len(ids), len(set(ids)))
            for item in DATA[section]:
                self.assertIn(item['language'], DATA['languages'])
                self.assertTrue(item['title'])
                if section != 'references':
                    self.assertTrue(item['code'].strip())
                    self.assertIn('output', item)
                if section == 'lessons':
                    quiz = item['quiz']
                    self.assertTrue(0 <= quiz['answer'] < len(quiz['choices']))
                    self.assertTrue(item['exercise'])
                    self.assertGreaterEqual(len(item['paragraphs']), 2)

    def test_python_snippets_are_syntactically_valid(self):
        for section in ('lessons', 'examples', 'algorithms'):
            for item in DATA[section]:
                if item['language'] == 'python':
                    compile(item['code'], item['id'], 'exec')


class ProgressTests(unittest.TestCase):
    setUp = base.AppTests.setUp
    tearDown = base.AppTests.tearDown
    send = base.AppTests.send
    register = base.AppTests.register
    get = base.AppTests.get

    def test_progress_is_owned_by_each_user(self):
        first = self.register()
        response = self.send('/api/progress/python-variables', {'completed':True}, csrf=first['csrf'], method='PUT')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.get('/api/progress').json['progress']['python-variables'])
        second_client = self.app.test_client()
        self.register('second_student', second_client)
        self.assertEqual(self.get('/api/progress', second_client).json['progress'], {})

    def test_progress_requires_csrf_and_valid_lesson(self):
        first = self.register()
        self.assertEqual(self.send('/api/progress/python-variables', {'completed':True}, method='PUT').status_code, 403)
        for lesson, value in [('nonexistent', True), ('python-variables','yes'), ('python-variables',1)]:
            self.assertEqual(self.send('/api/progress/'+lesson, {'completed':value}, csrf=first['csrf'], method='PUT').status_code, 400)

    def test_guest_progress_survives_conversion_and_can_be_unmarked(self):
        guest = self.send('/api/guest').json
        self.send('/api/progress/python-variables', {'completed':True}, csrf=guest['csrf'], method='PUT')
        student = self.register()
        self.assertTrue(self.get('/api/progress').json['progress']['python-variables'])
        self.send('/api/progress/python-variables', {'completed':False}, csrf=student['csrf'], method='PUT')
        self.assertFalse(self.get('/api/progress').json['progress']['python-variables'])
