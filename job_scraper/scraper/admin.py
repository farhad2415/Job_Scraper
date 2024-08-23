from django.contrib import admin

# Register your models here.

from .models import ScrapedData, AvilableUrl, Job

admin.site.register(ScrapedData)
admin.site.register(AvilableUrl)
admin.site.register(Job)
