from datetime import timedelta

import pdfplumber
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import ManuscriptFilter, ManuscriptForm
from .models import Author, Category, Conference, Journal, Manuscript, Venue
from ..labpulse.decorators import GroupRequiredMixin

class PaginationUtil:
    def __init__(self, view, paginate_by):
        self.view = view
        self.paginate_by = paginate_by

    def paginate_queryset(self, queryset):
        paginator = Paginator(queryset, self.paginate_by)
        page = self.view.request.GET.get('page')

        try:
            paginated_queryset = paginator.page(page)
        except PageNotAnInteger:
            paginated_queryset = paginator.page(1)
        except EmptyPage:
            paginated_queryset = paginator.page(paginator.num_pages)

        return paginated_queryset
class ManuscriptListView(GroupRequiredMixin, LoginRequiredMixin, ListView):
    login_url = 'login'  # Specify the login URL
    required_groups = ['repository_authors', 'repository_readers']
    model = Manuscript
    template_name = 'repo/manuscript_lists.html'  # Change this to your desired template
    context_object_name = 'all_manuscripts'  # Define the context variable name
    paginate_by = 10  # Set the number of items per page

    def get_queryset(self):
        queryset = Manuscript.objects.all()
        filter = ManuscriptFilter(self.request.GET, queryset=queryset)
        return filter.qs


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Manuscript List'  # Replace with your desired title

        # Create an instance of PaginationUtil and use its paginate_queryset method
        pagination_util = PaginationUtil(self, self.paginate_by)
        context['qi_list'] = pagination_util.paginate_queryset(self.get_queryset())

        context['filter_form'] = ManuscriptFilter(self.request.GET, queryset=self.get_queryset())
        # Calculate the current time *** minutes ago to hide delete button
        context['time_to_hide_button'] = timezone.now() - timedelta(minutes=120)

        return context


def count_pages(file_path):
    with pdfplumber.open(file_path) as pdf:
        number_of_pages = len(pdf.pages)
    return number_of_pages


class ManuscriptUpdateView(GroupRequiredMixin, LoginRequiredMixin, UpdateView):
    login_url = 'login'  # Specify the login URL
    required_groups = ['repository_authors']
    model = Manuscript
    form_class = ManuscriptForm  # Use your ManuscriptForm
    template_name = 'repo/add_repo.html'  # Change this to your desired template
    context_object_name = 'manuscript'  # Define the context variable name

    def get_absolute_url(self, **kwargs):
        return reverse_lazy('manuscript_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        if form.is_valid():
            manuscript = form.save(commit=False)
            # Count the number of pages using pdfplumber
            pdf_file = form.cleaned_data['pdf_file']
            if pdf_file:
                # Count the number of pages using pdfplumber
                manuscript.number_of_pages = count_pages(pdf_file)
                # Save the file size in bytes
                manuscript.file_size = pdf_file.size
            manuscript.save()
            # Manually set the authors after saving the manuscript
            form.save_m2m()
            return redirect(self.get_absolute_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update Manuscript'  # Replace with your desired title
        return context


class ManuscriptDeleteView(GroupRequiredMixin, LoginRequiredMixin, DeleteView):
    login_url = 'login'  # Specify the login URL
    required_groups = ['repository_authors']
    model = Manuscript
    template_name = 'repo/delete_page.html'
    context_object_name = 'manuscript'
    success_url = reverse_lazy('manuscript_list')  # Redirect to a list view after deletion

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Delete Manuscript'
        return context


class ManuscriptDetailView(GroupRequiredMixin, LoginRequiredMixin, DetailView):
    login_url = 'login'  # Specify the login URL
    required_groups = ['repository_authors', 'repository_readers']
    model = Manuscript
    template_name = 'repo/manuscript_details.html'  # Replace with your desired template name
    context_object_name = 'manuscript'  # Define the context variable name for the single manuscript

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'UON FYJ'  # Replace with your desired title
        return context


class ManuscriptCreateView(GroupRequiredMixin, LoginRequiredMixin, CreateView):
    login_url = 'login'  # Specify the login URL
    required_groups = ['repository_authors']
    model = Manuscript
    template_name = 'repo/add_repo.html'  # Replace with your template name
    form_class = ManuscriptForm  # Replace with your actual form class

    def get_success_url(self):
        # Redirect to the detail view of the updated manuscript
        return reverse_lazy('manuscript_detail', kwargs={'pk': self.object.pk})

    def count_pages(self, file_path: str) -> int:
        with pdfplumber.open(file_path) as pdf:
            number_of_pages = len(pdf.pages)
        return number_of_pages

    def form_valid(self, form):
        if form.is_valid():
            manuscript = form.save(commit=False)
            # Check if pdf_file is present in the form
            if 'pdf_file' in form.cleaned_data and form.cleaned_data['pdf_file']:
                pdf_file = form.cleaned_data['pdf_file']
                # Count the number of pages using pdfplumber
                manuscript.number_of_pages = self.count_pages(pdf_file)
                # Save the file size in bytes
                manuscript.file_size = pdf_file.size

            manuscript.save()
            # Manually set the authors after saving the manuscript
            form.save_m2m()
            return super().form_valid(form)

        # If form is not valid, re-render the template with the form and pre-selected authors
        return render(self.request, self.template_name, {'form': form})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'UON FYJ'  # Replace with your desired title
        return context


class AuthorCreateView(GroupRequiredMixin, LoginRequiredMixin, CreateView):
    login_url = 'login'  # Specify the login URL
    required_groups = ['repository_authors']
    model = Author
    template_name = 'repo/add_repo_data.html'  # Change this to the desired template
    fields = ['first_name', 'last_name']
    success_url = reverse_lazy('create_manuscript')  # Change 'author-list' to your actual URL name

    def form_valid(self, form):
        form.instance.first_name = form.cleaned_data['first_name'].upper()
        form.instance.last_name = form.cleaned_data['last_name'].upper()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add Author'  # Replace with your desired title
        context['all_authors'] = Author.objects.all()
        return context


class AuthorUpdateView(GroupRequiredMixin, LoginRequiredMixin, UpdateView):
    login_url = 'login'  # Specify the login URL
    required_groups = ['repository_authors']
    model = Author
    template_name = 'repo/add_repo_data.html'  # Change this to the desired template
    fields = ['first_name', 'last_name']
    success_url = reverse_lazy('create-author')  # Change 'create_manuscript' to your actual URL name

    def form_valid(self, form):
        form.instance.first_name = form.cleaned_data['first_name'].upper()
        form.instance.last_name = form.cleaned_data['last_name'].upper()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update Author'  # Replace with your desired title
        return context


class CategoryCreateView(GroupRequiredMixin, LoginRequiredMixin, CreateView):
    login_url = 'login'  # Specify the login URL
    required_groups = ['repository_authors']
    model = Category
    template_name = 'repo/add_repo_data.html'  # Change this to the desired template
    fields = ['name']
    success_url = reverse_lazy('create_manuscript')  # Change 'category-list' to your actual URL name

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add Category'  # Replace with your desired title
        context['all_categories'] = Category.objects.all()
        return context


class CategoryUpdateView(GroupRequiredMixin, LoginRequiredMixin, UpdateView):
    login_url = 'login'  # Specify the login URL
    required_groups = ['repository_authors']
    model = Category
    template_name = 'repo/add_repo_data.html'  # Change this to the desired template
    fields = ['name']
    success_url = reverse_lazy('create-category')  # Change 'create_manuscript' to your actual URL name

    def form_valid(self, form):
        form.instance.name = form.cleaned_data['name']
        # form.instance.last_name = form.cleaned_data['last_name'].upper()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add Category'  # Replace with your desired title
        return context


#
class JournalCreateView(GroupRequiredMixin, LoginRequiredMixin, CreateView):
    login_url = 'login'  # Specify the login URL
    required_groups = ['repository_authors']
    model = Journal
    template_name = 'repo/add_repo_data.html'  # Change this to the desired template
    fields = ['name']
    success_url = reverse_lazy('create_manuscript')  # Change 'journal-list' to your actual URL name

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add Journal'  # Replace with your desired title
        context['all_journals'] = Journal.objects.all()
        return context


class JournalUpdateView(GroupRequiredMixin, LoginRequiredMixin, UpdateView):
    login_url = 'login'  # Specify the login URL
    required_groups = ['repository_authors']
    model = Journal
    template_name = 'repo/add_repo_data.html'  # Change this to the desired template
    fields = ['name']
    success_url = reverse_lazy('create-journal')  # Change 'create_manuscript' to your actual URL name

    def form_valid(self, form):
        form.instance.name = form.cleaned_data['name']
        # form.instance.last_name = form.cleaned_data['last_name'].upper()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add Category'  # Replace with your desired title
        return context

class ConferenceCreateView(GroupRequiredMixin, LoginRequiredMixin, CreateView):
    login_url = 'login'  # Specify the login URL
    required_groups = ['repository_authors']
    model = Conference
    template_name = 'repo/add_repo_data.html'  # Change this to the desired template
    fields = ['name']
    success_url = reverse_lazy('create_manuscript')  # Change 'journal-list' to your actual URL name

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add Conference'  # Replace with your desired title
        context['all_journals'] = Conference.objects.all()
        return context


class ConferenceUpdateView(GroupRequiredMixin, LoginRequiredMixin, UpdateView):
    login_url = 'login'  # Specify the login URL
    required_groups = ['repository_authors']
    model = Conference
    template_name = 'repo/add_repo_data.html'  # Change this to the desired template
    fields = ['name']
    success_url = reverse_lazy('create-journal')  # Change 'create_manuscript' to your actual URL name

    def form_valid(self, form):
        form.instance.name = form.cleaned_data['name']
        # form.instance.last_name = form.cleaned_data['last_name'].upper()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add Conference'  # Replace with your desired title
        return context

class VenueCreateView(GroupRequiredMixin, LoginRequiredMixin, CreateView):
    login_url = 'login'  # Specify the login URL
    required_groups = ['repository_authors']
    model = Venue
    template_name = 'repo/add_repo_data.html'  # Change this to the desired template
    fields = ['name']
    success_url = reverse_lazy('create_manuscript')  # Change 'journal-list' to your actual URL name

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add Venue'  # Replace with your desired title
        context['all_journals'] = Venue.objects.all()
        return context


class VenueUpdateView(GroupRequiredMixin, LoginRequiredMixin, UpdateView):
    login_url = 'login'  # Specify the login URL
    required_groups = ['repository_authors']
    model = Venue
    template_name = 'repo/add_repo_data.html'  # Change this to the desired template
    fields = ['name']
    success_url = reverse_lazy('create-journal')  # Change 'create_manuscript' to your actual URL name

    def form_valid(self, form):
        form.instance.name = form.cleaned_data['name']
        # form.instance.last_name = form.cleaned_data['last_name'].upper()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add Venue'  # Replace with your desired title
        return context

