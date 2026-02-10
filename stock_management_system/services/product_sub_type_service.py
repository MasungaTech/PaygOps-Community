from payg_loan_system.devices.model.product_sub_type import ProductSubType
from shared.services.base_getter_service import BaseGetterService
from shared.logger.loggers import Error
from shared.services.base_service import BaseService
from shared.services.settings_service import SettingsService

class ProductSubTypeService(BaseGetterService, BaseService):

    OBJ_NAME = 'Product Sub-Type'

    @classmethod
    def get_filtered_objects(cls, current_user, device_type=None, is_serialized=None, **kwargs):
        subtypes = ProductSubType.select()
        if device_type:
            subtypes = subtypes.filter(lambda pst: pst.device_type == device_type)
        if is_serialized is not None:
            subtypes = subtypes.filter(lambda pst: pst.is_serialized == is_serialized)
        return subtypes
        
    @classmethod
    def validate_data(cls, data, editing=None):

        if 'is_serialized' in data:
            if editing and data['is_serialized'] != editing.is_serialized:
                raise Error('You cannot edit the serialized status if there are devices associated')
            if not data.get('is_serialized', True) and data['device_type'] != 'NPG':
                raise Error('PAYGO products must be serialized')
        
        if 'device_type' in data or not editing:
            if not data['device_type'] in SettingsService.get_setting('AllDeviceAPIS').keys() and data['device_type'] != 'NPG':
                raise Error('Product type {type} is not configured in the platform', type=data['device_type'])

        if 'name' in data or not editing:
            data['name'] = data['name'].strip()
            cls._check_name(data['name'], data.get('device_type', editing.device_type if editing else None), editing)
        
        if 'sku' in data:
            data['sku'] = data['sku'].strip()
            cls._check_sku(data['sku'], editing)
        

    @classmethod
    def _add_from_data_and_user(cls, data, user):
        cls.validate_data(data)
        return ProductSubType(
            name=data['name'],
            sku=data.get('sku') or None,
            device_type=data['device_type'],
            is_serialized=data.get('is_serialized', True)
        )

    @classmethod
    def _edit_from_data_and_user(cls, product_sub_type, data, user):
        cls.validate_data(data, product_sub_type)
        
        if 'is_serialized' in data:
            product_sub_type.is_serialized = data['is_serialized']

        if 'name' in data:
            product_sub_type.name = data['name']

        if 'sku' in data:
            product_sub_type.sku = data['sku'] or None

        if 'device_type' in data:
            product_sub_type.device_type = data['device_type']

        return product_sub_type

    @classmethod
    def _check_sku(cls, sku, existing_product_sub_type=None):
        if sku and len(sku) > 12:
            raise Error('SKU must be alphanumeric and a maximum of 12 characters.')
        eid = existing_product_sub_type.id if existing_product_sub_type else -1
        if sku and ProductSubType.get(lambda pst: pst.sku == sku and pst.id != eid):
            raise Error('Product sub-type SKU is already taken.')
        
    @classmethod
    def delete_from_object_and_user(cls, product_sub_type, user):
        if product_sub_type.quantity_stock_locations:
            raise Error('The product sub-type cannot be deleted because there are quantities linked to this product sub-type.')

        if product_sub_type.devices:
            raise Error('The product sub-type cannot be deleted because there are devices linked to this product sub-type.')

        if product_sub_type.offers:
            raise Error(f'The product sub-type cannot be deleted because there are offers that are restricted to this sub-type.')

        if product_sub_type.addon_offers:
            raise Error(f'The product sub-type cannot be deleted because there are add-on offers that are restricted to this sub-type.')

        product_sub_type.delete()

    @classmethod
    def _check_name(cls, name, device_type, existing_product_sub_type=None):
        if not name:
            raise Error('Product sub-types needs to have a name')
        
        eid = existing_product_sub_type.id if existing_product_sub_type else -1
        if ProductSubType.get(lambda pst: pst.name == name and pst.id != eid and pst.device_type == device_type):
            raise Error('Product sub-type name is already taken.')
