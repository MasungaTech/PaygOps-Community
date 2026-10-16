from shared.services.base_getter_service import BaseGetterService
from payg_loan_system.contracts.models.addon_category import AddOnCategory
from shared.logger.loggers import Error


class AddonCategoryService(BaseGetterService):

    OBJ_NAME = 'Add-on Category'

    @classmethod
    def _add_from_data_and_user(cls, data, user=None):
        parent_name = data.get('parent')
        if AddOnCategory.exists(name=data['name']):
            raise Error('The category '+data['name']+' already exists')
        parent = cls.get_from_user_and_properties(user, name=parent_name) if parent_name else None
        if parent_name and not parent:
            raise Error(f"Parent category "+data.get('parent')+" not found")
        if parent:
            parent.before_update()
        return AddOnCategory(
            name=data['name'],
            parent=parent
        )

    @classmethod
    def _edit_from_data_and_user(cls, category, data, user):
        if category.is_system():
            raise Error('CANNOT_EDIT_SYSTEM_CATEGORY')
        if 'name' in data:
            existing = AddOnCategory.get(name=data['name'])
            if existing and existing != category:
                raise Error('The category '+data['name']+' already exists')
            category.name = data['name']
        if 'parent' in data:
            parent_name = data['parent']
            if parent_name:
                parent = AddonCategoryService.get_from_user_and_properties(user, name=parent_name)
                if not parent:
                    raise Error(f'Parent category {parent_name} not found')
                category.parent = parent
            else:
                category.parent = None
        return category

    @classmethod
    def get_filtered_objects(cls, current_user, search='', with_results=None, excluded='', **kwargs):
        categories = AddOnCategory.select()
        if excluded:
            categories = categories.filter(lambda c: c.name.lower() not in excluded)
        if 'parent' in kwargs:
            categories = categories.filter(lambda c: c.parent == kwargs['parent'])
        if search:
            categories = categories.filter(lambda c: search.lower() in c.name.lower())
        if with_results == 'offers':
            categories = categories.filter(lambda c: c.covered_offers.count() != 0)
        elif with_results == 'bundles':
            categories = categories.filter(lambda c: c.covered_bundles.count() != 0)
        return categories

    @classmethod
    def _delete_from_object_and_user(cls, category, user):
        if category.children:
            raise Error('The category cannot be delete since it has children categories')
        if category.addon_offers:
            raise Error('The category cannot be delete since it has add-on offers assigned')
        category.delete()
