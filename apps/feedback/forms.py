from django import forms
from .models import App, Feedback, Response


class FeedbackForm(forms.ModelForm):
    app_name = forms.ModelChoiceField(queryset=App.objects.all(), empty_label='Select an app', required=True)

    class Meta:
        model = Feedback
        fields = ('user_feedback',)
        widgets = {
            'user_feedback': forms.Textarea(attrs={'size': '40', 'rows': '4'})
        }
        labels = {
            'user_feedback': 'Your Feedback',
        }

    def __init__(self, *args, **kwargs):
        """
        Initialize the FeedbackForm, setting the initial value for the app_name field if an instance is provided.

        This method customizes the initialization of the form by pre-filling the 'app_name' field with the app
        associated with the given feedback instance (if available). This is particularly useful when editing
        an existing feedback, ensuring that the form shows the correct app associated with that feedback.

        Parameters:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments. Expected to include:
            - instance: The Feedback instance being edited, if any.
            - initial: A dictionary of initial values for form fields (optional).

        Modifies:
        - kwargs['initial']: Updates the 'initial' dictionary to include the app associated with the feedback
          instance under the 'app_name' key, if the instance is provided and has an associated app.

        Calls:
        - super().__init__(*args, **kwargs): Calls the parent class's __init__ method to complete the form
          initialization with the modified 'initial' values.

        Example:
            form = FeedbackForm(instance=feedback_instance)
        """
        instance = kwargs.get('instance')
        initial = kwargs.setdefault('initial', {})
        if instance and instance.app:
            initial['app_name'] = instance.app
        super().__init__(*args, **kwargs)


class ResponseForm(forms.ModelForm):
    class Meta:
        model = Response
        fields = ('response_text',)
