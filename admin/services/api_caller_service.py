from shared.api_helpers.api_structure import API_STRUCTURE, API_STRUCTURE_NAMES
from werkzeug.exceptions import NotFound

from shared.api_helpers.documented_resource import DocumentedResource


class APICallerService:

    @classmethod
    def get_action_docs(cls, action, user, error=NotFound):
        subaction = ''
        if ':' in action:
            action, subaction = action.split(':')
        resource_name, method = action.split('_')
        resource = API_STRUCTURE_NAMES[resource_name]
        docs = cls.get_resource_method_docs(resource, method, user, raise_error=error)
        if subaction:
            docs['subaction'] = resource.SUBACTIONS[method][subaction]
        docs['generators'] = resource.API_CALLER_GENERATORS.get(method, {})
        return docs

    @classmethod
    def get_resource_method_docs(cls, resource, method, user, raise_error=NotFound):
        if issubclass(resource, DocumentedResource):
            docs = resource.docs_get_metadata()
            public_with_permission = resource.PUBLIC and (not resource.VIEW_DOCS_PERMISSION or user.can_access_in_scope(resource.VIEW_DOCS_PERMISSION))
            allowed_and_not_deprecated = method in resource.ALLOWED_API_CALLER and method in docs and not docs[method].get('deprecated')
            if public_with_permission and allowed_and_not_deprecated:
                return docs[method]
        if raise_error:
            raise raise_error
    
    @classmethod
    def get_summary(cls, resource, method, user):
        docs = APICallerService.get_resource_method_docs(resource, method, user, raise_error=False)
        return docs['summary'] if docs else None
    
    @classmethod
    def get_subactions(cls, resource, method):
        subactions = {}
        if method in resource.SUBACTIONS:
            method_subactions = resource.SUBACTIONS[method]
            subactions.update({
                resource.__name__+"_"+method: {
                    subaction: data['name'] for subaction, data in method_subactions.items()
                }
            })
        return subactions
    
    @classmethod
    def get_action_list(cls, user):
        actions = {}
        subactions = {}
        for r in API_STRUCTURE:
            if issubclass(r, DocumentedResource):
                for m in r._methods:
                    summary = APICallerService.get_summary(r, m, user)
                    if summary:
                        actions[r.__name__+"_"+m] = summary
                        subactions.update(cls.get_subactions(r, m))
        return actions, subactions