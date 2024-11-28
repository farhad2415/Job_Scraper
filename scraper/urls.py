from django.urls import path
from . import views
urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('view_scraped_data/', views.view_scraped_data, name='view_scraped_data'),
    path('start_scraping/', views.scrape_job, name='start_scraping'),
    path('update-phone-number/<int:job_id>/', views.update_phone_number, name='update_phone_number'),
    path('update-salary/<int:job_id>/', views.update_salary, name='update_salary'),
    path('', views.home, name='home'),
    path('export_to_excel/', views.export_to_excel, name='export_to_excel'),
    path('confirm-delete-jobs/', views.confirm_delete_jobs, name='confirm_delete_jobs'),
]