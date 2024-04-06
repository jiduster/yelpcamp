from django.urls import (path)
from . import apps

# 这里的路由是localhost:8081/api/list, 因为在server/urls.py里面api已经include了
urlpatterns = [
    path("/list", apps.list, name="list"),
    path("/detail", apps.detail, name='detail'),
    path("/comments", apps.comments, name='comments'),
    path("/comments/add", apps.commentAdd, name='commentAdd'),
    path("/upload", apps.upload, name="upload"),
    path("/file", apps.file, name="file"),
    path("/add", apps.campAdd, name="add")
]