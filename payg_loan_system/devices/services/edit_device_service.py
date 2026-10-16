from datetime import datetime
from payg_loan_system.devices.model.device import DeviceTag
from shared.logger.loggers import Error
from stock_management_system.services.product_sub_type_service import ProductSubTypeService


class DeviceEditService:


    @classmethod
    def edit_from_data_and_user(cls, device, device_data_dict, user):

        if device.stock_item.reserved:
            raise Error(
                '''You cannot edit a device that has a pending movement,
                please approve or reject the movement before editing'''
            , 'DEVICE_RESERVED')
        current_sub_type = device.product_sub_type.id if device.product_sub_type else None
        pst_id = device_data_dict.get('product_sub_type_id')
        if 'product_sub_type_id' in device_data_dict and pst_id != current_sub_type:
            user.check_access('EditSubTypeDevices')
            product_sub_type_id = ProductSubTypeService.get_from_user_and_id(user, pst_id, strict=True) if pst_id else None
            device.product_sub_type = product_sub_type_id

        can_edit_tags = user.can_access('EditTagsDevices')
        can_create_tags = user.can_access('CreateTagsDevices')

        tags = device_data_dict.get('tags')
        if tags is not None:
            if not can_edit_tags:
                raise Error('INSUFFICIENT_PERMISSION', permission='EditTagsDevices')

            if not isinstance(tags, list):
                tags = tags.split(',')
            try:
                tags_id = [int(t) for t in tags]
                updated_tags = DeviceTag.select(lambda t: t.id in tags_id)
            except ValueError:
                updated_tags = DeviceTag.select(lambda t: t.name in tags)

            device.tags = updated_tags
            device.tag_added()

        add_tags = device_data_dict.get('add_tags')
        if add_tags:
            for tag in add_tags:
                this_tag = DeviceTag.get(name=tag)
                if this_tag:
                    if not can_edit_tags:
                        raise Error('INSUFFICIENT_PERMISSION', permission='EditTagsDevices')
                    device.tags.add(this_tag)
                else:
                    if not can_create_tags:
                        raise Error('INSUFFICIENT_PERMISSION', permission='CreateTagsDevices')
                    device.tags.create(name=tag)
            device.tag_added()

        remove_tags = device_data_dict.get('remove_tags')
        if remove_tags:
            for tag in remove_tags:
                this_tag = DeviceTag.get(name=tag)
                if this_tag:
                    if not can_edit_tags:
                        raise Error('INSUFFICIENT_PERMISSION', permission='EditTagsDevices')
                    device.tags.remove(this_tag)
                    
        device.modifiedDate = datetime.now()
        device.stock_item.modifiedDate = datetime.now()
        
        return device
