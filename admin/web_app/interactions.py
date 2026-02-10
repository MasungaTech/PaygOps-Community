from flask import render_template, request, abort
from flask_login import current_user, login_required
from pony.orm import db_session, select

import config
from admin.token_generator_service import TokenCreator
from admin.web_app import administration
from shared.helpers.authorizer import authorizer
from survey_system.services.form_getter_service import FormGetterService
from shared.helpers.pagination import Pagination

if config.ENABLE_ENTERPRISE_FEATURES:
    from after_sales_system.interaction_system.model.interaction_report_model import \
        InteractionTopicGroup
    from after_sales_system.interaction_system.services.interaction_topic_group_getter_service import \
        InteractionTopicGroupGetterService
    from after_sales_system.interaction_system.services.interaction_topic_service import \
        InteractionTopicService
    from after_sales_system.issue_system.services.issue_type_service import \
        IssueTypeService
else:
    InteractionTopicGroup = None
    InteractionTopicGroupGetterService = None
    InteractionTopicService = None
    IssueTypeService = None

@administration.route('/interactions/settings/', methods=['GET'])
@login_required
@authorizer('EditInteractionsSettingsForms')
@db_session
def interaction_settings():
    if not config.ENABLE_ENTERPRISE_FEATURES:
        return abort(404)
    Themes = {t.id: t.name for t in InteractionTopicGroupGetterService.get_list(current_user)}
    surveys = {s.id: s.name for s in FormGetterService.get_filtered_objects(current_user, for_interactions=True)}
    issue_types ={t.id: t.name for t in IssueTypeService.get_list(current_user)}
    main_topic_id = request.args.get('main_topic_id')
    if main_topic_id:
        selected_theme = InteractionTopicGroup.get(id=main_topic_id)
        topics = InteractionTopicService.get_filtered_objects(current_user, group_id=main_topic_id)
    else:
        topics = InteractionTopicService.get_filtered_objects(current_user)
        selected_theme = None
    categories = InteractionTopicGroupGetterService.get_list(current_user)
    issuesType = IssueTypeService.get_list(current_user)
    pagination = Pagination.generate(request, default_sort='id:desc')
    pagination.objects = topics

    return render_template('settings/settings_editor_after_sales.html',
                            pagination=pagination,
                            Themes=Themes,
                            selected_theme=selected_theme,
                            topics=topics,
                            surveys=surveys,
                            categories=categories,
                            issues=issuesType,
                            issue_types=issue_types)
