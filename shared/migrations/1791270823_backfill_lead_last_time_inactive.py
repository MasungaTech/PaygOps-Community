from pony.orm import db_session

from sales_system.leads.models.lead import Lead
from sales_system.leads.models.lead_status import LeadStatus
from sales_system.leads.models.status_category import BILLING_INACTIVE_CATEGORIES
from sales_system.leads.models.status_change_history import StatusChangesHistory


@db_session
def up(db):
    # last_time_inactive used to be refreshed by inactive -> inactive status changes. Reset it to
    # the date of the last active -> inactive transition found in the status history (an inactive
    # status change whose previous change was active, or the lead's first change).
    # Single pass with a window function: correlated subqueries per lead get very slow when the
    # planner has no statistics (e.g. right after a restore).
    # History rows are written a few microseconds before the lead timestamp, hence the
    # 1 minute tolerance to leave untouched leads that never had an inactive -> inactive change.
    inactive_categories = ', '.join(f"'{c}'" for c in BILLING_INACTIVE_CATEGORIES)
    lead_table = Lead._table_
    status_table = LeadStatus._table_
    history_table = StatusChangesHistory._table_

    db.execute(f'''
        WITH history AS (
            SELECT
                h.lead,
                h.date,
                s.category IN ({inactive_categories}) AS is_inactive,
                LAG(s.category IN ({inactive_categories}))
                    OVER (PARTITION BY h.lead ORDER BY h.date, h.id) AS previous_is_inactive
            FROM "{history_table}" h
            JOIN "{status_table}" s ON s.id = h.status_id
        ),
        last_transition AS (
            SELECT history.lead, MAX(history.date) AS date
            FROM history
            JOIN "{lead_table}" l2 ON l2.id = history.lead
            WHERE history.is_inactive
              AND history.previous_is_inactive IS NOT TRUE
              AND history.date <= l2.last_time_inactive
            GROUP BY history.lead
        )
        UPDATE "{lead_table}" AS l
        SET last_time_inactive = last_transition.date
        FROM last_transition
        WHERE last_transition.lead = l.id
          AND last_transition.date < l.last_time_inactive - INTERVAL '1 minute'
    ''')


@db_session
def down(db):
    pass
