from django.db import models

# Create your models here.
# chat/models.py



class ChatMessage(models.Model):
    question = models.CharField(max_length=255)
    answer = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Question: {self.question}, Answer: {self.answer}"
