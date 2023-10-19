from celery.result import AsyncResult
from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIRequestFactory

from .models import File
from .serializers import FileSerializer
from .tasks import process_uploaded_file
from .views import FileUploadView, FileListView


test_file_data = b'This is a test file content.'
test_file = SimpleUploadedFile("test_file.txt", test_file_data)


class FileUploadViewTestCase(TestCase):
    def test_file_upload_valid(self):
        client = Client()
        test_file_data = b'This is a test file content.'
        test_file = SimpleUploadedFile("test_file.txt", test_file_data)
        response = client.post('/api/v1/upload/', {'file': test_file})
        self.assertEqual(response.status_code, 201)

    def test_file_upload_invalid(self):
        client = Client()
        response = client.post('/api/v1/upload/', {})
        self.assertEqual(response.status_code, 400)


class FileListViewTestCase(TestCase):
    def test_file_list(self):
        factory = APIRequestFactory()
        request = factory.get('/api/v1/files/')
        view = FileListView.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)


class FileModelTestCase(TestCase):
    def setUp(self):
        self.file = File.objects.create(file=test_file)

    def test_file_str(self):
        self.assertEqual(str(self.file), self.file.file.name)

    def test_file_processed_default(self):
        self.assertFalse(self.file.processed)


class FileSerializerTestCase(TestCase):
    def test_file_serializer_valid(self):
        data = {'file': test_file}
        serializer = FileSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_file_serializer_invalid(self):
        data = {}
        serializer = FileSerializer(data=data)
        self.assertFalse(serializer.is_valid())


class CeleryTestCase(TestCase):
    def test_process_uploaded_file(self):
        factory = APIRequestFactory()
        request = factory.post('/api/v1/upload/', {'file': test_file}, format='multipart')
        view = FileUploadView.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 201)
        file = File.objects.latest('uploaded_at')
        task = process_uploaded_file.apply_async(args=(file.id, 'application/pdf'))

        task_result = AsyncResult(task.id)
        task_result.get()

        self.assertEqual(task_result.state, 'SUCCESS')
