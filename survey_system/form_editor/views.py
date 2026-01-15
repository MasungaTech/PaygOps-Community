from payg_loan_system.offers.models import Offer, OfferType
from survey_system.models.question import Question
from core_system.person.models.form_visibility import FormVisibilityScope, FormVisibilityRule
from survey_system.models.question_type import QuestionType, PictureType
from werkzeug.exceptions import NotFound
from flask_login import login_required
from flask_login import current_user
from flask import render_template, request, redirect, url_for, send_file
from pony import orm
from shared.helpers.select2 import render
import config
from shared.helpers.authorizer import authorizer
from survey_system.form_editor.blueprint import forms_blueprint
from survey_system.form_editor.services import FormSorter
from survey_system.models.forms import FormVersion, Form
from admin.token_generator_service import TokenCreator
from shared.helpers.pagination import Pagination
from survey_system.services.form_getter_service import FormGetterService, FormVersionGetterService
from survey_system.services.question_getter_service import QuestionGetterService
from shared.services.paygops_package_exporter import PaygOpsPackageExporter

@forms_blueprint.route('/', methods=['GET'])
@login_required
@authorizer('ViewForms')
@orm.db_session
def list_forms():
    availabilities = {
        'leads': lambda w: w.for_leads,
        'clients': lambda w: w.for_clients,
        'interactions': lambda w: w.for_interactions
    }
    filter_avail = request.form.get('availability', request.args.get('availability', ''))
    forms = Form.select()
    if filter_avail in availabilities:
        forms = forms.filter(availabilities[filter_avail])
    params = 'availability={}'.format(filter_avail)
    pagination = Pagination.generate(request, params=params, default_sort='id:desc')
    if pagination.search:
        forms = forms.filter(lambda f: pagination.search.lower() in f.name.lower())
    pagination.objects = FormSorter.sort(forms, pagination.sort)
    return render_template('list_forms.html', pagination=pagination, filter_avail=filter_avail)


@forms_blueprint.route('/view/<int:form_id>')
@login_required
@orm.db_session
def view_form(form_id):
    form = FormGetterService.get_from_user_and_id(current_user, form_id, strict=True, main_resource=True)
    new = not form.versions.count()
    if new:
        version_number = 1
    else:
        try:
            version_number = int(request.args.get('version', form.last_version_number))
        except (ValueError, TypeError):
            raise NotFound
    version = form.versions.select(lambda v: v.version == version_number).first()
    if not version and not new:
        raise NotFound
    configured_for_leads = FormVisibilityRule.select(lambda c: c.form == form and c.scope in FormVisibilityScope._lead_scopes())
    configured_for_clients = FormVisibilityRule.select(lambda c: c.form == form and c.scope in FormVisibilityScope._client_scopes())
    configured_for_interactions = bool(form.interaction_topics.count())

    form_questions = orm.select(oq.question for v in form.versions for oq in v.questions)
    questions_select = {q.id: q.name+' (from '+getattr(q.get_form(), 'name', '')+')' for q in Question.select(lambda q: q not in form_questions).order_by(Question.name)}

    l = [t for t in QuestionType.to_list() if t not in [QuestionType.group, QuestionType._input_type, QuestionType._human_codes]]
    types_dict = {t: QuestionType.to_human(t) for t in sorted(l, key=QuestionType.to_human)}
    picture_types = {m: PictureType.to_human(m) for m in sorted(PictureType.to_list())}
    print(picture_types)
    return render_template('view_form.html', form=form, version=version, types=QuestionType.to_human,
                           next=request.args.get('next', False), configured_for_leads=configured_for_leads,
                           configured_for_clients=configured_for_clients, configured_for_interactions=configured_for_interactions,
                           questions_select=questions_select, types_dict=types_dict, picture_types=picture_types)
    
@forms_blueprint.route('/questions/<int:question_id>/view')
@login_required
@orm.db_session
def view_question(question_id):
    question = QuestionGetterService.get_from_user_and_id(current_user, question_id, strict=True, main_resource=True)
    return render_template('view_question.html', question=question, types=QuestionType.to_human)


@forms_blueprint.route('/questions/<int:question_id>/edit')
@login_required
@orm.db_session
def edit_question(question_id):
    question = QuestionGetterService.get_from_user_and_id(current_user, question_id, strict=True, main_resource=True)
    l = [t for t in QuestionType.to_list() if t not in [QuestionType.group, QuestionType._input_type, QuestionType._human_codes]]
    types_dict = {t: QuestionType.to_human(t) for t in sorted(l, key=QuestionType.to_human)}
    picture_types = {m: PictureType.to_human(m) for m in sorted(PictureType.to_list())}
    return render_template('edit_question.html', question=question, types=QuestionType.to_human, types_dict=types_dict, picture_types=picture_types)


@forms_blueprint.route('/preview/<int:form_id>')
@login_required
@orm.db_session
def preview_form(form_id):
    form = FormGetterService.get_from_user_and_id(current_user, form_id, strict=True, main_resource=True)
    try:
        version_number = int(request.args.get('version', form.last_version_number))
    except (ValueError, TypeError):
        raise NotFound
    version = form.versions.select(lambda v: v.version == version_number).first()
    if not version:
        raise NotFound
    return render_template('preview_form.html', form=form, version=version)


@forms_blueprint.route('/download/<int:form_version_id>')
@login_required
@orm.db_session
def download_form(form_version_id):
    # Get the form
    version = FormVersionGetterService.get_from_user_and_id(current_user, form_version_id, strict=True)
    # Send ZIP file
    return PaygOpsPackageExporter.export_form_version(version)
