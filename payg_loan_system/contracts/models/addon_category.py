from datetime import datetime
from shared.api_helpers.client_helpers.uuid_generation_helpers import generate_uuid
from shared.helpers.date_helper import getCurrentUtcDate, getDefaultDateStr
from shared.logger.loggers import Error
from pony.orm import Required, Optional, Set, count, select
from shared.api_helpers.model_definition_base import ModelDefinitionMixin
from core_system.core_entities import db


class AddOnCategory(db.Entity, ModelDefinitionMixin):

    name = Required(str, unique=True)
    parent = Optional("AddOnCategory", reverse="children", column="parent")
    children = Set("AddOnCategory")
    addon_offers = Set("AddOnOffer")
    addon_bundles = Set("ContractAddOnBundle")
    ascendants = Set("AddOnCategory", column="higher")
    descendants = Set("AddOnCategory", column="lower")
    modifiedDate = Required(datetime, default=datetime.now, index=True, column="modified_date", volatile=True)
    mobile_uuid = Optional(str, unique=True)

    allowed_on_offers = Set("Offer")

    # To be deleted after migration
    old_addon_offers_versions = Set("AddOnOfferVersion") 

    def is_system(self):
        return self.name == 'Contract Terms Changes'

    @property
    def modified_date(self):
        return self.modifiedDate

    def get_breadcrumbs(self, initial=None):
        if initial == self:
            raise Error('Inifinite loop in categories hierarchy')
        return [self] + (self.parent.get_breadcrumbs(initial=(initial or self)) if self.parent else [])

    @property
    def covered_offers(self):
        return db.AddOnOffer.select(lambda o: o.category == self or o.category in self.descendants)

    @property
    def covered_bundles(self):
        return db.ContractAddOnBundle.select(lambda o: o.category == self or o.category in self.descendants)

    def get_breadcrumbs_text(self):
        from shared.services.translation_service import TranslationService
        import markupsafe
        all_text = TranslationService.ftext('All', current=True)
        breadcrumbs = self.get_breadcrumbs()[::-1] if self.children else self.get_breadcrumbs()[:0:-1]
        result = '<a href="#" data-cat-id="">'+all_text+'</a><span> > </span>' + '<span> > </span>'.join([f'<a href="#" data-cat-id="{c.id}">{c.name}</a>' for c in breadcrumbs])
        return markupsafe.Markup(result)

    def check_data_coherence(self):
        if self.parent == self:
            raise Error('A category cannot be the parent of itself')
        if len(self.get_breadcrumbs()) > 5:
            raise Error('The maximum level of depth in categories hierarchy is 5')
    
    def before_insert(self):
        if not self.mobile_uuid:
            self.mobile_uuid = generate_uuid()
        self.check_data_coherence()

    def before_update(self):
        self.modifiedDate = datetime.now()
        self.check_data_coherence()

    def after_update(self):
        self.rebuild_ascendants()
        for ao in self.addon_offers:
            ao.modifiedDate = datetime.now()
        for ab in self.addon_bundles:
            ab.modifiedDate = datetime.now()

    def after_insert(self):
        self.rebuild_ascendants()

    def before_delete(self):
        if self.parent:
            self.parent.modifiedDate = datetime.now()

    def rebuild_ascendants(self):
        self.ascendants.clear()
        if self.parent:
            self.ascendants.add(self.parent)
            self.ascendants.add(self.parent.ascendants)
        for child in self.children:
            child.rebuild_ascendants()

    @classmethod
    def get_model_definition(cls, op, **kwargs):
        return {
            'properties': {
                "name": {
                    "type": "string",
                    "example": "Small Product",
                    "description": "The name of the category",
                    "value": lambda o: o.name
                },
                "parent": {
                    "type": "string",
                    "example": "Product",
                    "description": "The name of the parent category if any",
                    "value": lambda o: o.parent.name if o.parent else None
                },
                "children": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "example": ["Bateries", "Cables"],
                    "description": "The list of children categories if any",
                    "value": lambda o: [c.name for c in o.children]
                },
                "addon_offers": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "The IDs of the offers under this category",
                    "example": [1, 2, 3],
                    "value": lambda o: [a.id for a in o.addon_offers]
                },
                "addon_bundles": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "The IDs of the bundles under this category",
                    "example": [1, 2, 3],
                    "value": lambda o: [a.id for a in o.addon_bundles]
                }
            },
            'view_required': [],
            'view_allowed': [],
            'edit_required': [],
            'edit_allowed': ["name", "parent"],
            'create_allowed': ["name", "parent"],
            'create_required': ["name"]
        }

