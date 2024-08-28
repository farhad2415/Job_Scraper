from django.urls import path
from . import views
urlpatterns = [
    path('view_scraped_data/', views.scrape_view, name='scrape_job_details'),
    path('start_scraping/', views.scrape_job, name='start_scraping'),
    path('', views.home, name='home'),
    path('export_to_excel/', views.export_to_excel, name='export_to_excel'),
]