import pandas as pd
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.views.generic import DeleteView

from .models import App, Feedback, Response
from .forms import AppForm, FeedbackForm, ResponseForm
from ..cqi.views import bar_chart


@login_required(login_url='login')
def feedback_list(request):
    response_distribution_fig = app_summary_fig = None

    # Get all feedbacks and annotate with the number of responses
    feedbacks = Feedback.objects.annotate(num_responses=Count('response'))

    # Filter out feedbacks with no responses
    # feedbacks_with_responses = feedbacks.annotate(num_responses=Count('response'))
    feedbacks_with_responses = feedbacks.filter(num_responses__gt=0)

    # Group feedbacks by app and count the number of feedbacks for each app
    feedbacks_by_app = Feedback.objects.values('app__name').annotate(num_feedbacks=Count('id'))
    # Create a DataFrame from the queryset with custom column names
    df_feedbacks_by_app = pd.DataFrame(list(feedbacks_by_app))

    if df_feedbacks_by_app.shape[0] > 0:
        df_feedbacks_by_app.columns = ['Source', 'Feedbacks']
        df_feedbacks_by_app.sort_values("Feedbacks", inplace=True)
        ###################################
        # SUMMARY CHART
        ###################################
        total_feedback = df_feedbacks_by_app['Feedbacks'].sum()
        app_summary_fig = bar_chart(df_feedbacks_by_app, 'Source', 'Feedbacks',
                                    f"Distribution of Number of User Feedback per source  N = {total_feedback}",
                                    xaxis_title="Sources of user feedback")

        ###################################
        # FEEDBACK VS RESPONSES
        ###################################
        # Group responses by app and count the number of responses for each app
        responses_by_app = Response.objects.values('feedback__app__name').annotate(num_responses=Count('id'))

        df_responses_by_app = pd.DataFrame(list(responses_by_app))
        if df_responses_by_app.shape[0] > 0:
            df_responses_by_app.columns = ['Source', 'Responses']

            total_response = df_responses_by_app['Responses'].sum()
            response_rate = round(total_response / total_feedback * 100, 1)

            # Merge the two DataFrames on the 'Source' column (app name)
            df_merged = pd.merge(df_feedbacks_by_app, df_responses_by_app, on='Source', how='outer').fillna(0)

            df_merged = pd.melt(df_merged, id_vars="Source",
                                value_vars=list(df_merged.columns[1:]),
                                var_name="feedback vs response", value_name='#')

            response_distribution_fig = bar_chart(df_merged, "Source", "#",
                                                  f"User Feedback vs Responses      Response rate {response_rate}% "
                                                  f"({total_response}/{total_feedback})",
                                                  color="feedback vs response", yaxis_title="Counts",
                                                  xaxis_title="", legend_title="feedback vs response")

    context = {'feedbacks': feedbacks, 'feedbacks_with_responses': feedbacks_with_responses,
               'app_summary_fig': app_summary_fig, "response_distribution_fig": response_distribution_fig,
               "view_type": "view"}
    return render(request, 'feedback/feedback_list.html', context)


@login_required(login_url='login')
def apps_list(request):
    apps = App.objects.all()
    return render(request, 'feedback/apps_list.html', {'apps': apps})


@login_required(login_url='login')
def app_detail(request, pk):
    app = get_object_or_404(App, id=pk)
    feedbacks = Feedback.objects.filter(app=app)
    return render(request, 'feedback/app_detail.html', {'app': app, 'feedbacks': feedbacks})


@login_required(login_url='login')
def create_app(request):
    apps = App.objects.all()
    if request.method == 'POST':
        form = AppForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('create_app')
    else:
        form = AppForm()
    context = {'form': form, "apps": apps, "view_type": "add_app"}
    return render(request, 'feedback/submit_feedback.html', context)


@login_required(login_url='login')
def update_app(request, pk):
    app = get_object_or_404(App, id=pk)
    if request.method == 'POST':
        form = AppForm(request.POST, instance=app)
        if form.is_valid():
            form.save()
            return redirect('create_app')
    else:
        form = AppForm(instance=app)
    return render(request, 'feedback/submit_feedback.html',
                  {'form': form, 'feedback': app, "view_type": "add_app"})


@login_required(login_url='login')
def delete_app(request, pk):
    app = get_object_or_404(App, id=pk)
    if request.method == 'POST':
        form = AppForm(request.POST, instance=app)
        if form.is_valid():
            form.save()
            return redirect('create_app')
    else:
        form = AppForm(instance=app)
    return render(request, 'feedback/submit_feedback.html',
                  {'form': form, 'feedback': app, "view_type": "add_app"})


class AppDeleteView(LoginRequiredMixin, DeleteView):
    login_url = 'login'  # Specify the login URL
    model = App
    template_name = 'feedback/delete_page.html'
    success_url = reverse_lazy('create_app')  # Redirect to a list view after deletion

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


@login_required(login_url='login')
def feedback_detail(request, pk):
    # Retrieve the feedback object with the given primary key (pk)
    feedback = get_object_or_404(Feedback, id=pk)

    # Annotate the feedback object with the count of related responses
    # This counts the number of responses associated with the feedback
    feedback.num_responses = feedback.response_set.count()
    return render(request, 'feedback/feedback_detail.html', {'feedback': feedback})


@login_required(login_url='login')
def submit_feedback(request):
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.created_by = request.user
            feedback.app = App.objects.get(name__icontains=form.cleaned_data['app_name'])
            feedback.save()
            return redirect('app_detail', pk=feedback.app.id)
    else:
        form = FeedbackForm()
    context = {'form': form, "view_type": "submit"}
    return render(request, 'feedback/submit_feedback.html', context)


@login_required(login_url='login')
def update_feedback(request, pk):
    feedback = get_object_or_404(Feedback, id=pk)

    if request.method == 'POST':
        form = FeedbackForm(request.POST, instance=feedback)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.app = form.cleaned_data['app_name']
            form.save()
            return redirect('feedback_detail', pk=feedback.id)
    else:
        form = FeedbackForm(instance=feedback)

    return render(request, 'feedback/submit_feedback.html', {'form': form, 'feedback': feedback})


@login_required(login_url='login')
def feedback_with_response(request):
    # Query all feedback objects that have associated responses
    feedback_with_responses = Feedback.objects.filter(response__isnull=False).distinct()
    # Create a context dictionary to store feedbacks and their responses
    feedback_response_dict = {}
    for feedback in feedback_with_responses:
        feedback_response_dict[feedback] = feedback.response_set.all()
    context = {'feedback_response_dict': feedback_response_dict}
    # Pass the feedback objects with their responses to the template
    return render(request, 'feedback/feedback_with_response.html', context)


@login_required(login_url='login')
def feedback_without_response(request):
    # Query all feedback objects that do not have associated responses
    feedback_without_responses = Feedback.objects.filter(response__isnull=True)

    # Pass the feedback objects without responses to the template
    return render(request, 'feedback/feedback_without_response.html', {'feedbacks': feedback_without_responses})


@login_required(login_url='login')
def respond_to_feedback(request, pk):
    feedback = get_object_or_404(Feedback, id=pk)
    try:
        response = Response.objects.get(feedback_id=feedback.id)
        has_response = True
    except Response.DoesNotExist:
        response = None
        has_response = False
    if request.method == 'POST':
        form = ResponseForm(request.POST)
        if form.is_valid():
            response = form.save(commit=False)
            response.feedback = feedback
            response.created_by = request.user
            response.save()
            return redirect('app_detail', pk=feedback.app.id)
    else:
        form = ResponseForm()

    context = {'form': form, 'feedback': feedback, 'has_response': has_response, 'response': response, }
    return render(request, 'feedback/respond_to_feedback.html', context)


@login_required(login_url='login')
def update_response(request, pk):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    response = get_object_or_404(Response, id=pk)
    feedback = response.feedback

    if request.method == 'POST':
        form = ResponseForm(request.POST, instance=response)
        if form.is_valid():
            form.save()

            # Redirect and then clear the session data
            redirect_url = request.session.get('page_from', '/')
            if 'page_from' in request.session:
                del request.session['page_from']
            return redirect(redirect_url)
    else:
        form = ResponseForm(instance=response)
    context = {'form': form, 'response': response, 'feedback': feedback}
    return render(request, 'feedback/respond_to_feedback.html', context)
