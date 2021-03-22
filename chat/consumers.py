import json
import logging
import threading
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.datetime_safe import datetime
import pika, sys, os
from .models import Message, ChatRoom
import logging

logger = logging.getLogger(__name__)


class ChatConsumer(WebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.thread = None

    def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['roomname']
        self.room_group_name = 'chat_%s' % self.room_name
        self.room_group_name = str(self.scope['user'].id)
        user = self.scope['user']
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )

        if self.thread is None:
            self.thread = threading.Thread(target=self.receive_from_queue, args=(user.id,))
            self.thread.start()
        logger.debug("connected")
        self.accept()

    def disconnect(self, close_code):
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    # When user click send button in the chat, receives message from websocket
    def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        sender_userid = text_data_json['sender_userid']
        receiver_userid = text_data_json['receiver_userid']

        # Save Message in the database
        try:
            room_name = ChatRoom.objects.get(user1_id=sender_userid, user2_id=receiver_userid)
        except ChatRoom.DoesNotExist:
            room_name, created = ChatRoom.objects.get_or_create(user1_id=sender_userid, user2_id=sender_userid)

        m = Message(message=message, sender_id=sender_userid, chatroom=room_name)
        m.save()

        # How to get the correct time zone after saving the date
        # message_db_obj = Message.objects.get(id=m.id)
        print(self.room_group_name, text_data_json)
        # Send message to room group
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'group': self.room_group_name,
                'sender_userid': sender_userid,
                'receiver_userid': receiver_userid,
                'timestamp': datetime.now().strftime("%-I:%M %p")
            }
        )

    def send_to_queue(self, queue_name, data):
        print(f"Thread {threading.get_ident()} send to queue", queue_name, data)
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='localhost'))
        channel = connection.channel()
        channel.queue_declare(queue=str(queue_name))
        # routing_key basically means queue to send to
        channel.basic_publish(exchange='', routing_key=str(queue_name), body=json.dumps(data))
        connection.close()

    def receive_from_queue(self, queue_name):
        connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        channel = connection.channel()
        channel.queue_declare(queue=str(queue_name))
        print(f"Thread {threading.get_ident()} receiver for queue", queue_name)

        def callback(ch, method, properties, body):
            # self.chat_message(json.loads(body))
            event = json.loads(body)
            print(f"Thread {threading.get_ident()} callback", queue_name, self.scope['user'].id, event)
            message = event['message']
            sender_userid = event['sender_userid']
            receiver_userid = event['receiver_userid']

            self.send(text_data=json.dumps({
                'message': message,
                'sender_userid': sender_userid,
                'sender_username': User.objects.get(id=sender_userid).username,
                'receiver_userid': receiver_userid,
                'receiver_username': User.objects.get(id=receiver_userid).username,
                'timestamp': event['timestamp']
            }))

        channel.basic_consume(queue=str(queue_name), on_message_callback=callback, auto_ack=True)
        channel.start_consuming()

    # Get the message from group
    def chat_message(self, event):
        message = event['message']
        sender_userid = event['sender_userid']
        receiver_userid = event['receiver_userid']

        # Send message to WebSocket
        # print(f"Thread {threading.get_ident()} receiver for queue", receiver_userid, event)
        # print(f"Thread {threading.get_ident()} receiver for queue", sender_userid, event)
        self.send_to_queue(receiver_userid, event)
        self.send_to_queue(sender_userid, event)
        # threading.Thread(target=self.send_to_queue, args=(receiver_userid, event)).start()
        # self.send(text_data=json.dumps({
        #     'message': message,
        #     'sender_userid': sender_userid,
        #     'sender_username': User.objects.get(id=sender_userid).username,
        #     'receiver_userid': receiver_userid,
        #     'receiver_username': User.objects.get(id=receiver_userid).username,
        #     'timestamp': event['timestamp']
        # }))
