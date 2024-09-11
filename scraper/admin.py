from django.contrib import admin

# Register your models here.

from .models import AvilableUrl, Job, Category, SubCategory

admin.site.register(AvilableUrl)
admin.site.register(Job)
admin.site.register(Category)
admin.site.register(SubCategory)

