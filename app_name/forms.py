# forms.py
from django import forms

class UploadFileForm(forms.Form):
    csv_file = forms.FileField(
        label="选择CSV文件",
        help_text="仅支持UTF-8编码的CSV文件",
        widget=forms.ClearableFileInput(attrs={'accept': '.csv'})
    )