from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'chat'
urlpatterns = [
    path('', views.index, name='index'),
    path('chat/<receiver_userid>',views.chat, name='chat'),
]
