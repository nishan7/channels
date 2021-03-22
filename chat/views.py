from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from django.contrib.auth.models import User
from .models import *


@login_required
def index(request):
    users = User.objects.all().exclude(id=request.user.id)
    return render(request, 'chat/index.html', {'users': users})


@login_required
def chat(request, receiver_userid):
    receiver_user = User.objects.get(id=receiver_userid)

    try:
        room_name = ChatRoom.objects.get(user1=request.user, user2=receiver_user)
    except ChatRoom.DoesNotExist:
        room_name, created = ChatRoom.objects.get_or_create(user1=receiver_user, user2=request.user)

    older_messages = Message.objects.filter(chatroom=room_name)
    return render(request, 'chat/chat.html', {'roomname': room_name.id,
                                              'older_messages': {},
                                              'receiver': receiver_user,
                                              'sender': request.user})
