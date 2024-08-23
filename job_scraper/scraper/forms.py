from django import forms
from .models import AvilableUrl, Job


class AvailableUrlForm(forms.ModelForm):
    class Meta:
        model = AvilableUrl
        fields = ['url']
        widgets = {
            'url': forms.Select(attrs={
                'class': 'form-control',
            })
        }
# make form for job
class JobFormModel(forms.Form):
    class Meta:
        model = Job
        fields = ['company', 'position', 'phone_number', 'email', 'website', 'vacancy', 'salary']
        widgets = {
            'company': forms.TextInput(attrs={
                'class': 'form-control',
            }),
            'position': forms.TextInput(attrs={
                'class': 'form-control',
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
            }),
            'vacancy': forms.TextInput(attrs={
                'class': 'form-control',
            }),
            'salary': forms.TextInput(attrs={
                'class': 'form-control',
            }),
        }
    