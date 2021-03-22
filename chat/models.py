from django.db import models
from django.contrib.auth.models import User


class ChatRoom(models.Model):
    user1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user1")
    user2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user2")

    class Meta:
        db_table = "Chat_Room"



class Message(models.Model):
    message = models.CharField(max_length=255)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sender")
    timestamp = models.DateTimeField(auto_now_add=True)
    chatroom = models.ForeignKey(ChatRoom, related_name="messages", on_delete=models.CASCADE)

    class Meta:
        db_table="message"
        ordering=['timestamp']
