from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget

# Register your models here.
from .models import AvilableUrl, Job, Category, SubCategory

admin.site.register(AvilableUrl)
admin.site.register(Category)
admin.site.register(SubCategory)



class JobResource(resources.ModelResource):
    class Meta:
        model = Job
        fields = ('id', 'position', 'company', 'location', 'job_type', 'description', 'job_posted', 'job_link', 'source', 'job_category', 'user', 'salary')
        export_order = ('id', 'position', 'company', 'location', 'job_type', 'description', 'job_posted', 'job_link', 'source', 'job_category', 'user', 'salary')

    def before_import_row(self, row, **kwargs):
        # Handle None values before saving
        if not row['position']:
            row['position'] = "Position not provided"
        
        if not row['company']:
            row['company'] = "Company not provided"

        if not row['location']:
            row['location'] = "Location not provided"
        
        if not row['job_type']:
            row['job_type'] = "Job type not provided"

        # Add other fields as necessary to avoid NoneType errors

        return super().before_import_row(row, **kwargs)
    
@admin.register(Job)
class JobAdmin(ImportExportModelAdmin):
    resources_class = JobResource
    list_display = ('company', 'position', 'location', 'job_type', 'description', 'job_posted', 'job_link', 'source', 'job_category', 'user', 'salary')
    search_fields = ('company', 'position', 'location', 'job_type', 'description', 'job_posted', 'job_link', 'source', 'job_category', 'user', 'salary')
    list_filter = ('company', 'position', 'location', 'job_type', 'description', 'job_posted', 'job_link', 'source', 'job_category', 'user', 'salary')