import io
import os
import shutil
import unittest
import zipfile
from unittest.mock import patch

import pandas as pd


TEST_DB = '/tmp/competition_feature_test.sqlite'
TEST_CERT_DIR = '/tmp/competition_feature_test_certs'
os.environ['DATABASE_URL'] = f'sqlite:///{TEST_DB}'
os.environ['CERT_STORAGE_DIR'] = TEST_CERT_DIR

if os.path.exists(TEST_DB):
    os.remove(TEST_DB)
if os.path.exists(TEST_CERT_DIR):
    shutil.rmtree(TEST_CERT_DIR, ignore_errors=True)

from app import app, db  # noqa: E402
from admin_auth import create_admin_token  # noqa: E402
from models import Application, ApplicationParticipant, ExcellentCoach  # noqa: E402
import certificate_routes  # noqa: E402


def _excel_bytes(rows):
    bio = io.BytesIO()
    pd.DataFrame(rows).to_excel(bio, index=False)
    bio.seek(0)
    return bio


class CertificateAdminFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        cls.client = app.test_client()
        with app.app_context():
            db.drop_all()
            db.create_all()

    def setUp(self):
        if os.path.exists(TEST_CERT_DIR):
            shutil.rmtree(TEST_CERT_DIR, ignore_errors=True)
        with app.app_context():
            db.session.remove()
            db.drop_all()
            db.create_all()

    def _admin_headers(self):
        with app.app_context():
            token = create_admin_token({'role': 'admin', 'username': 'admin'})
        return {'Authorization': f'Bearer {token}'}

    def _create_application(self, *, match_no='M001', teacher_name='张老师', teacher_phone='13800138000', award_level='一等奖'):
        app_row = Application(
            category='无人机足球',
            task='5v5',
            education_level='中学',
            participant_count=1,
            school_name='测试学校',
            contact_name='联系人',
            teacher_name=teacher_name,
            match_no=match_no,
            award_level=award_level,
            openid='openid-1'
        )
        app_row.contact_phone = '13900139000'
        app_row.contact_email = 'user@example.com'
        app_row.teacher_phone = teacher_phone
        app_row.participants.append(ApplicationParticipant(seq_no=1, participant_name='学生甲'))
        db.session.add(app_row)
        db.session.commit()
        return app_row.id

    def _create_coach(self, *, teacher_name='张老师', teacher_phone='13800138000'):
        coach = ExcellentCoach(teacher_name=teacher_name)
        coach.teacher_phone = teacher_phone
        db.session.add(coach)
        db.session.commit()
        return coach.id

    def test_import_awards_starts_player_task_by_default(self):
        with app.app_context():
            application_id = self._create_application(match_no='A100')

        with patch('certificate_routes._start_background_cert_task', return_value='player-task-1') as mocked_task:
            resp = self.client.post(
                '/api/admin/import-awards',
                data={'file': (_excel_bytes([{'参赛号': 'A100', '获奖等级': '一等奖'}]), 'awards.xlsx')},
                headers=self._admin_headers(),
                content_type='multipart/form-data'
            )

        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json()
        self.assertTrue(payload['success'])
        self.assertEqual(payload['data']['task_id'], 'player-task-1')
        mocked_task.assert_called_once_with(application_ids=[application_id], source=f"award-import:{payload['data']['import_log_id']}")

    def test_import_excellent_coaches_starts_task_by_default(self):
        with patch('certificate_routes._start_background_excellent_coach_task', return_value='coach-task-1') as mocked_task:
            resp = self.client.post(
                '/api/admin/import-excellent-coaches',
                data={'file': (_excel_bytes([{'指导老师姓名': '张老师', '指导老师电话': '13800138000'}]), 'coaches.xlsx')},
                headers=self._admin_headers(),
                content_type='multipart/form-data'
            )

        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json()
        self.assertTrue(payload['success'])
        self.assertEqual(payload['data']['task_id'], 'coach-task-1')
        self.assertEqual(mocked_task.call_count, 1)

    def test_excellent_coach_task_status_endpoint(self):
        task_id = 'coach-task-status'
        certificate_routes._write_json(
            certificate_routes._excellent_coach_task_path(task_id),
            {
                'task_id': task_id,
                'status': 'finished',
                'progress': {'total_coaches': 1, 'done_coaches': 1, 'generated_files': 1, 'errors': 0}
            }
        )

        resp = self.client.get(
            f'/api/admin/excellent-coach-certificate-tasks/{task_id}',
            headers=self._admin_headers()
        )
        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json()
        self.assertTrue(payload['success'])
        self.assertEqual(payload['data']['task_id'], task_id)

    def test_player_zip_names_files_by_match_no(self):
        with app.app_context():
            application_id = self._create_application(match_no='P888')
        certificate_routes._write_json(
            certificate_routes._task_path('player-zip-task'),
            {'application_ids': [application_id]}
        )
        os.makedirs(os.path.dirname(certificate_routes._cache_pdf_path('player', str(application_id))), exist_ok=True)
        with open(certificate_routes._cache_pdf_path('player', str(application_id)), 'wb') as f:
            f.write(b'%PDF-player')

        resp = self.client.get(
            '/api/admin/certificates/download-player-zip?task_id=player-zip-task',
            headers=self._admin_headers()
        )
        self.assertEqual(resp.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(resp.data)) as zf:
            self.assertIn('P888.pdf', zf.namelist())

    def test_excellent_coach_zip_names_files_by_related_match_no(self):
        with app.app_context():
            self._create_application(match_no='C666')
            coach_id = self._create_coach()
        certificate_routes._write_json(
            certificate_routes._excellent_coach_task_path('coach-zip-task'),
            {'coach_ids': [coach_id]}
        )
        os.makedirs(os.path.dirname(certificate_routes._cache_pdf_path('excellent_coach', str(coach_id))), exist_ok=True)
        with open(certificate_routes._cache_pdf_path('excellent_coach', str(coach_id)), 'wb') as f:
            f.write(b'%PDF-coach')

        resp = self.client.get(
            '/api/admin/excellent-coach-certificates/download-zip?task_id=coach-zip-task',
            headers=self._admin_headers()
        )
        self.assertEqual(resp.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(resp.data)) as zf:
            self.assertIn('C666.pdf', zf.namelist())


if __name__ == '__main__':
    unittest.main()
