import json
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.datetime_safe import datetime
import pika, sys, os
from .models import Message, ChatRoom


class ChatConsumer(WebsocketConsumer):
    def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['roomname']
        self.room_group_name = 'chat_%s' % self.room_name

        # # # Join room group
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )
        self.accept()
        print("connect")

    def disconnect(self, close_code):
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    # When user click send button in the chat
    def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        sender_userid = text_data_json['sender_userid']
        receiver_userid = text_data_json['receiver_userid']

        # Save Message in the database
        roomname = ChatRoom.objects.get(id=int(self.room_name))
        m = Message(message=message, sender=User.objects.get(id=sender_userid), chatroom=roomname)
        m.save()

        # How to get the correct time zone after saving the date
        # message_db_obj = Message.objects.get(id=m.id)

        # Send message to room group
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender_userid': sender_userid,
                'receiver_userid': receiver_userid,
                'timestamp': datetime.now().strftime("%-I:%M %p")
            }
        )

    def send_to_queue(self, queue_name, data):
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='localhost'))
        channel = connection.channel()
        channel.queue_declare(queue=queue_name)
        # routing_key basically means queue to send to
        channel.basic_publish(exchange='', routing_key=queue_name, body=json.dumps(data))
        connection.close()

    def receive_from_queue(self, queue_name):
        connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        channel = connection.channel()
        channel.queue_declare(queue=queue_name)

        def callback(ch, method, properties, body):
            self.chat_message(json.loads(body))

        channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)

        channel.start_consuming()

    def chat_message(self, event):
        message = event['message']
        sender_userid = event['sender_userid']
        receiver_userid = event['receiver_userid']

        # Send message to WebSocket
        self.send(text_data=json.dumps({
            'message': message,
            'sender_userid': sender_userid,
            'sender_username': User.objects.get(id=sender_userid).username,
            'receiver_userid': receiver_userid,
            'receiver_username': User.objects.get(id=receiver_userid).username,
            'timestamp': event['timestamp']
        }))
