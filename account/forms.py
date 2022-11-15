from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm


from django.forms import ModelForm
#
from account.models import NewUser


class NewUserForm(UserCreationForm):
    class Meta:
        model = NewUser
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_number', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        """This makes email field required"""
        super().__init__(*args, **kwargs)

        self.fields['username'].required = True
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['email'].required = True
        self.fields['phone_number'].required = True


class UpdateUserForm(ModelForm):
    class Meta:
        model = NewUser
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_number']
        exclude=('password1','password2',)

    def __init__(self, *args, **kwargs):
        """This makes email field required"""
        super().__init__(*args, **kwargs)

        self.fields['username'].required = True
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['email'].required = True
        self.fields['phone_number'].required = True
