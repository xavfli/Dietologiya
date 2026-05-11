from django import forms


class PriceSourceForm(forms.Form):
    city = forms.CharField(label="Shahar", max_length=80, initial="Tashkent", required=False, widget=forms.TextInput(attrs={"class": "form-control"}))


class MenuUploadForm(forms.Form):
    file = forms.FileField(label="Excel yoki ZIP fayl", widget=forms.FileInput(attrs={"class": "form-control", "accept": ".zip,.xlsx"}))


class TelegramSettingsForm(forms.Form):
    chat_id = forms.CharField(label="Telegram chat ID", max_length=120, widget=forms.TextInput(attrs={"class": "form-control"}))
    daily_digest = forms.BooleanField(label="Kunlik xulosa yuborish", required=False, initial=True, widget=forms.CheckboxInput(attrs={"class": "form-check-input"}))
