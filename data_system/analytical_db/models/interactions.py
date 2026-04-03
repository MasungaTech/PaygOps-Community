from datetime import datetime
from pony.orm import select, Set
from shared.helpers.db_helpers import Optional, PrimaryKey
from data_system.analytical_db.analytical_db import analytical_db
from data_system.analytical_db.models.base_analytical_db_model import BaseAnalyticalDBModel
import config

if config.ENABLE_ENTERPRISE_FEATURES:
    from after_sales_system.interaction_system.model.interaction_report_model import InteractionMethod, InteractionReport
else:
    # Stub classes for when enterprise features are disabled
    class InteractionReport:
        pass
    class InteractionMethod:
        @staticmethod
        def to_human(_):
            return 'not_available'


class Interactions(analytical_db.Entity, BaseAnalyticalDBModel):

    _description_ = 'Interactions are reports of actual interactions with a client. This is usually used to track the different calls or visit needed to resolve an issue, as well as more friendly interactions or satisfaction surveys. '

    base_model = InteractionReport

    id = PrimaryKey(int, comment="The internal unique ID of the interaction")
    entry_date = Optional(datetime, comment="The date at which the interaction was saved")
    interaction_date = Optional(datetime, comment="The date at which the interaction actually happened")
    interaction_method = Optional(str, comment="The method of the interaction (e.g. phone call, visit, SMS, etc.)")
    main_topic_name = Optional(str, comment="The main topic of the interaction (e.g. upsale, battery issue, etc.)")
    initiated_by_client = Optional(bool, comment="True if the client initiated the interaction (e.g. called the call center)")

    entry_by_user_id = Optional("Users", csv_columns=[("Entry User Name", lambda l: l.full_name)], comment="The internal ID of the user who entered the interaction", column="entry_by_user_id")
    client_id = Optional("Clients", csv_columns=[("Client Name", lambda l: l.full_name)], comment="The internal ID of the client who was involved in the interaction", column="client_id")
    main_issue_id = Optional("Issues", comment="The internal ID of the main issue that the interaction was related to (if any)", column="main_issue_id")

    # Virtual (not in table)
    question_answers = Set("Question_Answers")

    # Internal
    last_updated = Optional(datetime)

    @staticmethod
    def converter(interaction):
        return {
            "id": interaction[0],
            "entry_date": interaction[1],
            "interaction_date": interaction[2],
            "interaction_method": InteractionMethod.to_human(interaction[3]),
            "entry_by_user_id": interaction[4],
            "client_id": interaction[5],
            "main_topic_name": interaction[6] or '',
            "initiated_by_client": interaction[7],
            "main_issue_id": interaction[8],
            "last_updated": interaction[9]
        }

    @staticmethod
    def selector(objects):
        return select((
            i.id,
            i.entryDate,
            i.reportDate,
            i.method,
            i.userReporting.id,
            i.client.id,
            i.mainTopic.name,
            i.clientInitiated,
            min(topic.discussedIssue.id for topic in i.discussedTopics if topic.discussedIssue),
            Interactions.extended_modified_date(i)
        ) for i in objects).order_by(10)
