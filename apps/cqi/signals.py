from django.conf.global_settings import EMAIL_HOST_USER
from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.cqi.models import ActionPlan, Baseline, County_qi_projects, Hub_qi_projects, Milestone, Program_qi_projects, \
    QI_Projects, Qi_team_members, Subcounty_qi_projects, TestedChange


def get_project_level_details(instance):
    """
    Get the project level name and organization unit for a given project instance.

    This function takes a project instance and returns a tuple containing the project level name and
    organization unit. The project level name is the name of the facility, subcounty, county, hub, or
    program associated with the project, and the organization unit is the type of organization (e.g.,
    "Facility", "Subcounty", "County", "Hub", or "Program").

    Args:
        instance (QI_Projects | Subcounty_qi_projects | County_qi_projects | Hub_qi_projects | Program_qi_projects):
            The project instance for which to get the project level details.

    Returns:
        tuple: A tuple containing the project level name (str) and organization unit (str).
    """
    # Check the type of the project instance and get the corresponding project level name
    # and organization unit
    if isinstance(instance, QI_Projects):
        project_level_name = instance.facility_name.name
        organization_unit = "Facility"
    elif isinstance(instance, Subcounty_qi_projects):
        project_level_name = instance.sub_county.sub_counties
        organization_unit = "Subcounty"
    elif isinstance(instance, County_qi_projects):
        project_level_name = instance.county.county_name
        organization_unit = "County"
    elif isinstance(instance, Hub_qi_projects):
        project_level_name = instance.hub.hub
        organization_unit = "Hub"
    else:
        project_level_name = instance.program.program
        organization_unit = "Program"

    # Return the project level name and organization unit as a tuple
    return project_level_name, organization_unit


PROJECT_LEVEL_FIELDS = {
    QI_Projects: 'facility_name',
    Subcounty_qi_projects: 'sub_county',
    County_qi_projects: 'county',
    Hub_qi_projects: 'hub',
    Program_qi_projects: 'program',
}


@receiver(post_save, sender=QI_Projects)
@receiver(post_save, sender=Subcounty_qi_projects)
@receiver(post_save, sender=County_qi_projects)
@receiver(post_save, sender=Hub_qi_projects)
@receiver(post_save, sender=Program_qi_projects)
def send_project_creation_email(sender, instance, created, **kwargs):
    if created:
        user_email = instance.created_by.email
        user_name = instance.created_by.first_name.title() + " " + instance.created_by.last_name.title()
        qi_manager_email = instance.qi_manager.email
        subject = f"New Project Created: {instance.project_title}"

        # Determine project level
        project_level_name, organization_unit = get_project_level_details(instance)

        # Message for the creator
        creator_message = f"""
        <html>
            <body>                
                <p>Dear {instance.created_by.first_name} {instance.created_by.last_name},</p>
                <p>You have successfully created a new project with the following details:</p>
                <ul>
                    <li><b>Project Title:</b> {instance.project_title}</li>
                    <li><b>Problem Statement:</b> {instance.problem_background}</li>
                    <li><b>Objective:</b> {instance.objective}</li>
                    <li><b>Numerator:</b> {instance.numerator}</li>
                    <li><b>Denominator:</b> {instance.denominator}</li>
                    <li><b>QI Manager:</b> {instance.qi_manager}</li>
                    <li><b>Monitoring Frequency:</b> {instance.measurement_frequency}</li>                   
                    <li><b>{organization_unit}:</b> {project_level_name}</li>
                </ul>
                <p>Best regards,</p>
                <p>Peter</p>
                <p>Quality Improvement Specialist</p>
            </body>
        </html>
        """
        send_mail(subject, creator_message, EMAIL_HOST_USER, [user_email], html_message=creator_message)

        # Send email to the QI Manager
        qi_manager_message = f"""
                <html>
                    <body>                
                        <p>Dear {instance.qi_manager.first_name} {instance.qi_manager.last_name},</p>
                        <p>A new project has been created for you to oversee:</p>
                        <ul>
                            <li><b>Project Title:</b> {instance.project_title}</li>
                            <li><b>Problem Statement:</b> {instance.problem_background}</li>
                            <li><b>Objective:</b> {instance.objective}</li>
                            <li><b>Numerator:</b> {instance.numerator}</li>
                            <li><b>Denominator:</b> {instance.denominator}</li>
                            <li><b>Monitoring Frequency:</b> {instance.measurement_frequency}</li>
                            <li><b>{organization_unit}:</b> {project_level_name}</li>
                            <li><b>Project Created by:</b> {user_name}</li>
                            <li><b>Date Created:</b> {instance.start_date.strftime('%Y-%m-%d')}</li>
                        </ul>
                        <p>Please review and provide guidance as needed.</p>
                        <p>Best regards,</p>
                        <p>Peter</p>
                        <p>Quality Improvement Specialist</p>
                    </body>
                </html>
                """
        send_mail(subject, qi_manager_message, EMAIL_HOST_USER, [qi_manager_email], html_message=qi_manager_message)


PROJECT_MODEL_FIELDS = {
    QI_Projects: 'qi_project',
    Subcounty_qi_projects: 'subcounty_qi_project',
    County_qi_projects: 'county_qi_project',
    Hub_qi_projects: 'hub_qi_project',
    Program_qi_projects: 'program_qi_project',
}

TESTED_CHANGE_MODEL_FIELDS = {
    QI_Projects: 'project',
    Subcounty_qi_projects: 'subcounty_project',
    County_qi_projects: 'county_project',
    Hub_qi_projects: 'hub_project',
    Program_qi_projects: 'program_project',
}


@receiver(post_save, sender=QI_Projects)
@receiver(post_save, sender=Subcounty_qi_projects)
@receiver(post_save, sender=County_qi_projects)
@receiver(post_save, sender=Hub_qi_projects)
@receiver(post_save, sender=Program_qi_projects)
def send_missing_cqi_details_email(sender, instance, created, **kwargs):
    if created:
        project_field = PROJECT_MODEL_FIELDS.get(sender)
        tested_change_field = TESTED_CHANGE_MODEL_FIELDS.get(sender)
        if not project_field or not tested_change_field:
            return

        missing_milestones = Milestone.objects.filter(**{f'{project_field}': instance}).count() == 0
        missing_action_plan = ActionPlan.objects.filter(**{f'{project_field}': instance}).count() == 0
        missing_baseline = Baseline.objects.filter(**{f'{project_field}': instance}).count() == 0
        missing_qi_team_members = Qi_team_members.objects.filter(**{f'{project_field}': instance}).count() == 0
        missing_tested_change = TestedChange.objects.filter(**{f'{tested_change_field}': instance}).count() == 0
        missing_root_cause_analysis = not instance.process_analysis

        if missing_milestones or missing_action_plan or missing_baseline or missing_qi_team_members or \
                missing_tested_change or missing_root_cause_analysis:
            subject = "Complete Your QI Project Details: {}".format(instance.project_title)
            # Determine project level
            project_level_name, organization_unit = get_project_level_details(instance)

            # Message for the creator
            creator_message = """
            <html>
                <body>
                    <p>Dear {instance.created_by.first_name} {instance.created_by.last_name},</p>
                    <p>The following details are missing for the QI Project "{instance.project_title}" at 
                    {project_level_name} {organization_unit} level:</p>
                    <ul>
                        {missing_details}
                    </ul>
                    <p>Please update the project details accordingly. In case of any challenges, 
                    do not hesitate to contact platform admin.</p>
                    <p>Best regards,</p>
                    <p>Peter</p>
                    <p>Quality Improvement Specialist</p>
                </body>
            </html>
            """.format(instance=instance, project_level_name=project_level_name, organization_unit=organization_unit,
                       missing_details='\n'.join([
                           '<li>Baseline status</li>' if missing_baseline else '',
                           '<li>Root cause analysis</li>' if missing_root_cause_analysis else '',
                           '<li>QI team members</li>' if missing_qi_team_members else '',
                           '<li>Action Plan</li>' if missing_action_plan else '',
                           '<li>Milestones</li>' if missing_milestones else '',
                           '<li>Test of Change</li>' if missing_tested_change else ''
                       ]))

            # Message for the QI Manager
            qi_manager_message = """
            <html>
                <body>
                    <p>Dear {instance.qi_manager.first_name} {instance.qi_manager.last_name},</p>      
                    <p>The following details are missing for the QI Project you are overseeing, 
                    "{instance.project_title}" at {project_level_name} {organization_unit} level:</p>
                    <ul>
                        {missing_details}
                    </ul>
                    <p>Please help the team update the project details accordingly. In case of any challenges, 
                    do not hesitate to contact platform admin.</p>
                    <p>Best regards,</p>
                    <p>Peter</p>
                    <p>Quality Improvement Specialist</p>
                </body>
            </html>
            """.format(instance=instance, project_level_name=project_level_name, organization_unit=organization_unit,
                       missing_details='\n'.join([
                           '<li>Baseline status</li>' if missing_baseline else '',
                           '<li>Root cause analysis</li>' if missing_root_cause_analysis else '',
                           '<li>QI team members</li>' if missing_qi_team_members else '',
                           '<li>Action Plan</li>' if missing_action_plan else '',
                           '<li>Milestones</li>' if missing_milestones else '',
                           '<li>Test of Change</li>' if missing_tested_change else ''

                       ]))

            send_mail(subject, creator_message, EMAIL_HOST_USER, [instance.created_by.email],
                      html_message=creator_message)
            send_mail(subject, qi_manager_message, EMAIL_HOST_USER, [instance.qi_manager.email],
                      html_message=qi_manager_message)


PROJECT_TYPES = {
    'qi_project': {'field': 'qi_project', 'organization_unit': 'Facility', 'project_level_field': 'facility_name',
                   'project_type': 'single-cqi'},
    'program_qi_project': {'field': 'program_qi_project', 'organization_unit': 'Program',
                           'project_level_field': 'program', 'project_type': 'single-cqi-program'},
    'subcounty_qi_project': {'field': 'subcounty_qi_project', 'organization_unit': 'Subcounty',
                             'project_level_field': 'sub_county', 'project_type': 'single-cqi-subcounty'},
    'hub_qi_project': {'field': 'hub_qi_project', 'organization_unit': 'Hub', 'project_level_field': 'hub',
                       'project_type': 'single-cqi-hub'},
    'county_qi_project': {'field': 'county_qi_project', 'organization_unit': 'County', 'project_level_field': 'county',
                          'project_type': 'single-cqi-county'},
}


@receiver(post_save, sender=Qi_team_members)
def send_email_to_team_member(sender, instance, created, **kwargs):
    """
        Email a QI team member when they are added to a project.

        This function uses the `post_save` signal to send an email to a QI team member when they are added to a project.
        The email contains information about the project, including the project title, the team member's role, the project
        level, the organization unit, and a link to the project.
        """
    if created:
        # Find the project type based on the non-empty project field in the instance
        project_type = next(
            (project_type for project_type, config in PROJECT_TYPES.items() if getattr(instance, config['field'])),
            None)
        if not project_type:
            return

        project = getattr(instance, PROJECT_TYPES[project_type]['field'])
        organization_unit = PROJECT_TYPES[project_type]['organization_unit']
        project_level_field = PROJECT_TYPES[project_type]['project_level_field']
        project_level_name = getattr(project, project_level_field).sub_counties if project_level_field == 'sub_county' \
            else getattr(project,project_level_field).county_name if project_level_field == 'county' \
            else getattr(project, project_level_field).program
        project_type = PROJECT_TYPES[project_type]['project_type']

        subject = f"You're Added as a QI Team Member: {project.project_title}"

        # Construct the project URL
        project_url = f"https://cqi.fahariyajamii.org/{project_type}/{project.id}"

        # Construct the HTML email message
        message = f"""
        <html>
            <body>
                <p>Dear {instance.user.first_name.title()} {instance.user.last_name.title()},</p>

                <p>A new project has been created in the {organization_unit} '{project_level_name}' that you are involved in.</p>

                <ul>
                    <li><b>Project Title:</b> {project.project_title}</li>
                    <li><b>Your role:</b> {instance.role}</li>
                    <li><b>Project Level:</b> {organization_unit}</li>
                    <li><b>Organization Unit:</b> {project_level_name}</li>
                    <li><b>Project URL:</b> <a href="{project_url}">Click here</a></li>
                </ul>

                <p>Please review your involvement in the project and provide necessary contributions.</p>

                <p>Best regards,<br>
                Peter<br>
                Quality Improvement Specialist</p>
            </body>
        </html>
        """

        send_mail(subject, "", EMAIL_HOST_USER, [instance.user.email], html_message=message)
