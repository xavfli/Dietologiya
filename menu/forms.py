from django import forms
from django.conf import settings


class PriceSourceForm(forms.Form):
    city = forms.CharField(label="Shahar", max_length=80, initial="Tashkent", required=False, widget=forms.TextInput(attrs={"class": "form-control"}))


class MenuUploadForm(forms.Form):
    file = forms.FileField(label="Excel yoki ZIP fayl", widget=forms.FileInput(attrs={"class": "form-control", "accept": ".zip,.xlsx"}))

    def clean_file(self):
        uploaded = self.cleaned_data["file"]
        if not uploaded.name.lower().endswith((".zip", ".xlsx")):
            raise forms.ValidationError("Faqat .zip yoki .xlsx fayl yuklang.")
        if uploaded.size > settings.MENU_IMPORT_MAX_BYTES:
            max_mb = settings.MENU_IMPORT_MAX_BYTES // (1024 * 1024)
            raise forms.ValidationError(f"Fayl hajmi {max_mb} MB dan oshmasligi kerak.")
        return uploaded


class AIAgentForm(forms.Form):
    prompt = forms.CharField(
        label="AI agentga savol",
        min_length=5,
        max_length=2000,
        strip=True,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Masalan: oxirgi menyular va xarajatlar asosida qaysi jihatlarni yaxshilash kerak?",
            }
        ),
    )
