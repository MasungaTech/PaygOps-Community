from survey_system.models.forms import Form
from pony.orm import db_session
from datetime import timedelta


@db_session
def createReportTopics():
    from after_sales_system.interaction_system.model.interaction_report_model import (
        InteractionTopicGroup,
        InteractionTopic,
    )
    from after_sales_system.issue_system.model.issue_model import (
        IssueType,
        IssueTypeGroup,
    )
    otherotherTopicGroup = InteractionTopicGroup(name='Other')
    issueTopicGroup = InteractionTopicGroup(name='Issues')
    otherTopicGroup = InteractionTopicGroup(name='After-Sales')
    friendlyTopicGroup = InteractionTopicGroup(name='Friendly')
    paymentTopicGroup = InteractionTopicGroup(name='Reminders')
    changesTopicGroup = InteractionTopicGroup(name='Installation and Offer Change')
    businessTopicGroup = InteractionTopicGroup(name='Business Empowerment')

    InteractionTopic(name='Client absent', active=False, topicGroup=otherotherTopicGroup, form=Form.get(name='Friendly Talk'))

    InteractionTopic(name='Installation',
                    active=True, topicGroup=changesTopicGroup,
                    form=Form.get(name='Installation'))

    InteractionTopic(name='Upgrade Lease',
                    active=True, topicGroup=changesTopicGroup,
                    form=Form.get(name='Upgrade')) # TODO: Change

    InteractionTopic(name='Downgrade Lease',
                    active=True, topicGroup=changesTopicGroup,
                    form=Form.get(name='Downgrade')) # TODO: Change

    InteractionTopic(name='Uninstallation',
                    active=True, topicGroup=changesTopicGroup,
                    form=Form.get(name='Uninstallation')) # TODO: Change

    InteractionTopic(name='Support in activation',
                    active=True, topicGroup=otherTopicGroup,
                    form=Form.get(name='Support in Activation'))

    InteractionTopic(name='Remind to pay',
                    active=True, topicGroup=paymentTopicGroup,
                    form=Form.get(name='Remind to pay'))

    InteractionTopic(name='Business mentorship',
                    active=True, topicGroup=businessTopicGroup,
                    form=Form.get(name='Business mentorship'))

    InteractionTopic(name='Business training',
                    active=True, topicGroup=businessTopicGroup,
                    form=Form.get(name='Business training'))

    InteractionTopic(name='Business training assessment',
                    active=True, topicGroup=businessTopicGroup,
                    form=Form.get(name='Business training assessment'))

    InteractionTopic(name='Business follow-up',
                    active=True, topicGroup=businessTopicGroup,
                    form=Form.get(name='Business follow-up'))

    InteractionTopic(name='Phone Charging Review',
                    active=False, topicGroup=businessTopicGroup,
                    form=Form.get(name='Phone Charging Review'))

    InteractionTopic(name='Other',
                    active=True, topicGroup=otherotherTopicGroup,
                    form=Form.get(name='General Discussion'))

    InteractionTopic(name='General Discussion',
                    active=False, topicGroup=otherTopicGroup,
                    form=Form.get(name='General Discussion'))

    InteractionTopic(name='Reporting new Issue',
                    active=False, topicGroup=issueTopicGroup, form=Form.get(name='Other Issue'))

    InteractionTopic(name='Friendly talk', active=True, topicGroup=friendlyTopicGroup,
                    form=Form.get(name='Friendly Talk'))


    # Issue Type Groups
    accessoryIssues = IssueTypeGroup(name='Accessory Issues')
    systemIssues = IssueTypeGroup(name='System Issues')
    paymentIssues = IssueTypeGroup(name='Payment and Activation Issues')
    otherIssues = IssueTypeGroup(name='Other Issues')

    # Issue Types
    accessoryIssueType = IssueType(name='Accessory Issue', targetResolutionTime=timedelta(days=3), grouping=accessoryIssues)

    solarIssueType = IssueType(name='Solar Panel issue', targetResolutionTime=timedelta(days=4), grouping=systemIssues)
    batteryIssueType = IssueType(name='Battery issue', targetResolutionTime=timedelta(days=4), grouping=systemIssues)
    wiringIssueType = IssueType(name='Wiring issue', targetResolutionTime=timedelta(days=4), grouping=systemIssues)
    technicalIssueType = IssueType(name='System Issue', targetResolutionTime=timedelta(days=4), grouping=systemIssues)
    deviceChargingIssueType = IssueType(name='Device charging issue', targetResolutionTime=timedelta(days=4), grouping=systemIssues)
    otherDeviceIssueType = IssueType(name='Other device issue', targetResolutionTime=timedelta(days=4), grouping=systemIssues)
    paymentIssueType = IssueType(name='Payment Issue', targetResolutionTime=timedelta(days=1), grouping=paymentIssues)
    activationIssueType = IssueType(name='Activation Issue', targetResolutionTime=timedelta(days=1), grouping=paymentIssues)
    otherIssueType = IssueType(name='Other Issue', targetResolutionTime=timedelta(days=3), grouping=otherIssues)




    InteractionTopic(
        name="Accessory Issue",
        issueType=accessoryIssueType,
        active=True,
        topicGroup=issueTopicGroup,
        form=Form.get(name="Accessory Issue"),
    )

    InteractionTopic(
        name="Solar Panel Issue",
        issueType=solarIssueType,
        active=True,
        topicGroup=issueTopicGroup,
        form=Form.get(name="Solar Panel Issue"),
    )

    InteractionTopic(
        name="Battery Issue",
        issueType=batteryIssueType,
        active=True,
        topicGroup=issueTopicGroup,
        form=Form.get(name="Battery Issue"),
    )

    InteractionTopic(
        name="Wiring Issue",
        issueType=wiringIssueType,
        active=True,
        topicGroup=issueTopicGroup,
        form=Form.get(name="Wiring Issue"),
    )

    InteractionTopic(
        name="System Issue",
        issueType=technicalIssueType,
        active=True,
        topicGroup=issueTopicGroup,
        form=Form.get(name="System Issue"),
    )

    InteractionTopic(
        name="System Issue Details",
        issueType=technicalIssueType,
        active=True,
        topicGroup=issueTopicGroup,
        form=Form.get(name="System Issue Details"),
    )

    InteractionTopic(
        name="Other Issue",
        issueType=otherIssueType,
        active=True,
        topicGroup=issueTopicGroup,
        form=Form.get(name="Other Issue"),
    )

    InteractionTopic(
        name="Payment Issue",
        issueType=paymentIssueType,
        active=True,
        topicGroup=issueTopicGroup,
        form=Form.get(name="Payment Issue"),
    )

    InteractionTopic(
        name="Activation Issue",
        issueType=activationIssueType,
        active=True,
        topicGroup=issueTopicGroup,
        form=Form.get(name="Activation Issue"),
    )

    InteractionTopic(
        name="Device charging issue",
        issueType=deviceChargingIssueType,
        active=True,
        topicGroup=issueTopicGroup,
        form=Form.get(name="Device charging issue"),
    )

    InteractionTopic(
        name="Other device issue",
        issueType=otherDeviceIssueType,
        active=True,
        topicGroup=issueTopicGroup,
        form=Form.get(name="Other device issue"),
    )
