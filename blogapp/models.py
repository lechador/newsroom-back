from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.db import models
from tinymce.models import HTMLField

class User(AbstractUser):
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

class Category(models.Model):
    title = models.CharField(max_length=255)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')

    def __str__(self):
        return self.title
    
class Tag(models.Model):
    title = models.CharField(max_length=255)

    def __str__(self):
        return self.title

class Menu(models.Model):
    title = models.CharField(max_length=255)
    order_number = models.PositiveIntegerField()
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True)
    url_slug = models.SlugField(unique=True)

    def __str__(self):
        return self.title

class Comment(models.Model):
    blog = models.ForeignKey('Blog', on_delete=models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    parent_comment = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')
    likes = models.PositiveIntegerField(default=0)
    dislikes = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Comment by {self.author} on {self.blog}"



class Blog(models.Model):
    title = models.CharField(max_length=255)
    picture = models.ImageField(upload_to='blog_pictures/')
    description = HTMLField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True)
    tags = models.ManyToManyField('Tag', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.title