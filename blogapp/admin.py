from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Blog, Category, Tag, Menu, Comment

class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('profile_picture',)}),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('profile_picture',)}),
    )

@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'category', 'created_at', 'active')
    list_filter = ('category', 'tags', 'active')
    search_fields = ('title', 'author__username', 'category__title')


admin.site.register(User, CustomUserAdmin)
admin.site.register(Category)
admin.site.register(Tag)
admin.site.register(Menu)
admin.site.register(Comment)
