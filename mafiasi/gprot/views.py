import json
import time
import magic
from datetime import date

from nameparser import HumanName
from fuzzywuzzy import fuzz
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.core.mail import send_mail
from smtplib import SMTPException
from django.utils.translation import ugettext
from raven.contrib.django.raven_compat.models import client

from mafiasi.teaching.models import (Course, Teacher,
        insert_autocomplete_courses, insert_autocomplete_teachers)
from mafiasi.gprot.models import GProt, GProtNotification
from mafiasi.gprot.sanitize import clean_html

@login_required
def index(request):
    autocomplete_json = {'tokens': []}
    insert_autocomplete_courses(autocomplete_json)
    insert_autocomplete_teachers(autocomplete_json)

    search_json = []
    gprots = []
    if request.method == 'POST':
        course_pks = []
        teacher_pks = []

        # We have a search term that could not be resolved by
        # autocompletion on client. Try to search on server side
        term = request.POST.get('search', '').strip()
        if term:
            term_lower = term.lower()
            for token in autocomplete_json['tokens']:
                if token['token'].startswith(term_lower):
                    if token['type'] == 'course':
                        course_pks.append(token['pk'])
                    elif token['type'] == 'teacher':
                        teacher_pks.append(token['pk'])
        
        course_pks += request.POST.getlist('courses')
        courses = list(Course.objects.filter(pk__in=course_pks))
        for course in courses:
            search_json.append({
                'what': 'course',
                'pk': course.pk,
                'label': course.name
            })
        
        teacher_pks += request.POST.getlist('teachers')
        teachers = list(Teacher.objects.filter(pk__in=teacher_pks))
        for teacher in teachers:
            search_json.append({
                'what': 'teacher',
                'pk': teacher.pk,
                'label': teacher.get_full_name()
            })
        
        gprots = GProt.objects.select_related().filter(published=True)
        if courses:
            gprots = gprots.filter(course__pk__in=course_pks)
        if teachers:
            gprots = gprots.filter(examiner__pk__in=teacher_pks)
        
        # We have a search term with no matching courses/examiners
        if term and not (course_pks or teacher_pks):
            gprots = []


    return render(request, 'gprot/index.html', {
        'autocomplete_json': json.dumps(autocomplete_json),
        'search_json': json.dumps(search_json),
        'gprots': gprots
    })

@login_required
def create_gprot(request):
    autocomplete_courses = {'tokens': []}
    insert_autocomplete_courses(autocomplete_courses)
    autocomplete_examiners = {'tokens': []}
    insert_autocomplete_teachers(autocomplete_examiners)
    
    errors = {}
    course = None
    examiner = None
    exam_date = None
    course_name = ''
    examiner_name = ''
    exam_date_str = ''
    if request.method == 'POST':
        if 'course' in request.POST and request.POST['course'].isdigit():
            course = get_object_or_404(Course, pk=request.POST['course'])
        else:
            course_name = request.POST.get('course_name', '').strip()
            if not course_name:
                errors['course_name'] = True
            course = Course(name=course_name, short_name='')
        if 'examiner' in request.POST and request.POST['examiner'].isdigit():
            examiner = get_object_or_404(Teacher, pk=request.POST['examiner'])
        else:
            examiner_name = HumanName(request.POST.get('examiner_name', ''))
            if examiner_name.middle:
                first_name = u'{0} {1}'.format(examiner_name.first,
                                               examiner_name.middle)
            else:
                first_name = examiner_name.first
            last_name = examiner_name.last

            if not last_name:
                examiner = None
                errors['examiner_name'] = True
            else:
                examiner = Teacher(first_name=first_name, last_name=last_name,
                                   title=examiner_name.title)
        exam_date_str = request.POST.get('exam_date', '')
        try:
            exam_date_t = time.strptime(exam_date_str, '%Y-%m-%d')
            exam_date = date(exam_date_t.tm_year, exam_date_t.tm_mon,
                                 exam_date_t.tm_mday)
        except ValueError:
            errors['exam_date'] = True

        if 'type' in request.POST:
            if request.POST['type'] == 'html':
                is_pdf=False
            elif request.POST['type'] == 'pdf':
                is_pdf=True
            else:
                errors['type'] = True

        if not errors:
            if not course.pk:
                course.save()
            if not examiner.pk:
                examiner.save()
            gprot = GProt.objects.create(course=course,
                                         examiner=examiner,
                                         exam_date=exam_date,
                                         is_pdf=is_pdf,
                                         content='',
                                         author=request.user)
            return redirect('gprot_edit', gprot.pk)


    if course and course.pk:
        course_js = json.dumps({
            'label': course.name,
            'objData': {'pk': course.pk}
        })
    else:
        course_js = 'null'

    if examiner and examiner.pk:
        examiner_js = json.dumps({
            'label': examiner.get_full_name(),
            'objData': {'pk': examiner.pk}
        })
    else:
        examiner_js = 'null'

    return render(request, 'gprot/create.html', {
        'errors': errors,
        'course_name': course_name,
        'examiner_name': examiner_name,
        'exam_date_str': exam_date_str,
        'course_js': course_js,
        'examiner_js': examiner_js,
        'autocomplete_course_json': json.dumps(autocomplete_courses),
        'autocomplete_examiner_json': json.dumps(autocomplete_examiners)
    })

@login_required
def view_gprot(request, gprot_pk):
    gprot = get_object_or_404(GProt, pk=gprot_pk)
    if gprot.published or gprot.author == request.user:
        return render(request, 'gprot/view.html', {
            'gprot': gprot,
        })
    else:
        raise Http404

@login_required
def list_own_gprots(request):
    gprots = (GProt.objects.select_related().filter(author=request.user)
            .order_by('-exam_date'))
    return render(request, 'gprot/list_own.html', {
        'gprots': gprots
    })

@login_required
def edit_gprot(request, gprot_pk):
    gprot = get_object_or_404(GProt, pk=gprot_pk)
    if gprot.author != request.user:
        raise PermissionDenied('You are not the owner')

    error = ""
    if request.method == 'POST':
        if gprot.is_pdf:
            if "file" in request.FILES:
                upload = request.FILES['file']
                if upload.size > settings.GPROT_FILE_MAX_SIZE:
                    error = ugettext("<b>Error:</b> Only files up to 10 MB are allowed.")
                if magic.from_buffer(upload.read(1024), mime=True) != 'application/pdf':
                    error = ugettext("<b>Error:</b> Only PDF files are allowed.")
            else:
                error = ugettext("<b>Error:</b> Please select a file to upload.")

            if not error:
                if gprot.content_pdf:
                    gprot.content_pdf.delete()
                gprot.content_pdf = upload
                gprot.save()
        else:
            content = request.POST.get('content', '')
            gprot.content = clean_html(content)
            gprot.save()

        if not error:
            if 'publish' in request.POST:
                return redirect('gprot_publish', gprot.pk)
            else:
                return redirect('gprot_view', gprot.pk)

    return render(request, 'gprot/edit.html', {
        'gprot': gprot,
        'error': error
    })

@login_required
def publish_gprot(request, gprot_pk):
    gprot = get_object_or_404(GProt, pk=gprot_pk)
    if gprot.author != request.user:
        raise PermissionDenied('You are not the owner')

    if request.method == 'POST' and 'authorship' in request.POST:
        if request.POST['authorship'] == 'purge':
            gprot.author = None
        gprot.published = True
        gprot.save()
        notify_users(gprot, request)
        return redirect('gprot_view', gprot.pk)

    return render(request, 'gprot/publish.html', {
        'gprot': gprot
    })

def send_notification_email(gprot, notification, request):
    url = reverse('mafiasi.gprot.views.view_gprot', args=(gprot.pk,))
    email_content = render_to_string('gprot/notification_email.txt', {
        'notification': notification,
        'url': request.build_absolute_uri(url)
    })
    try:
        send_mail(ugettext(u'New memory minutes for "%(coursename)s"'
            % {'coursename': gprot.course.name}).encode('utf8'),
                email_content.encode('utf8'),
                None,
                [notification.user.email])
    except SMTPException as e:
        client.captureException()

def notify_users(gprot, request):
    """
    Notify users if a GProt matching one of their queries is published.
    """
    notified_users = []
    for notification in GProtNotification.objects.select_related() \
                        .filter(course_id__exact=gprot.course.pk):
        if notification.user not in notified_users:
            send_notification_email(gprot, notification, request)
            notified_users.append(notification.user)

    for notification in GProtNotification.objects.select_related() \
                        .filter(course_id=None):
        if notification.user not in notified_users and \
            fuzz.partial_ratio(notification.course_query, gprot.course.name) >= 67:
                send_notification_email(gprot, notification, request)
                notified_users.append(notification.user)



@login_required
def notifications(request):
    autocomplete_courses = {'tokens': []}
    insert_autocomplete_courses(autocomplete_courses)

    error = False

    if request.method == 'POST':
        notification = GProtNotification(added_date=date.today(),
                                         user=request.user)
        if 'course' in request.POST:
            course_pk = request.POST.get('course')
            try:
                course = Course.objects.get(pk=course_pk)
                notification.course = course
            except Course.DoesNotExist:
                error = True
        elif 'course_name' in request.POST:
            notification.course_query = request.POST['course_name']
        else:
            error = True

        if not error:
            notification.save()

    notifications = GProtNotification.objects.select_related() \
        .filter(user=request.user) \
        .order_by("-added_date")

    return render(request, 'gprot/notifications.html', {
        'notifications': notifications,
        'autocomplete_course_json': json.dumps(autocomplete_courses),
        'error': error
    })

@login_required
def delete_notification(request, notification_pk):
    notification = get_object_or_404(GProtNotification, pk=notification_pk)
    if request.user != notification.user:
        raise PermissionDenied('You are not the owner')

    notification.delete()

    return redirect('gprot_notifications')
