from django.db import models
from django.contrib.auth.models import User 

class UploadModel(models.Model):
    dataSource = models.CharField(max_length=255)
    filename = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    filePath = models.TextField()