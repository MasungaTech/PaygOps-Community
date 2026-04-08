import json
from io import BytesIO
from shared.api_helpers.server_helpers.json_serialization import CustomJSONEncoder
from zipfile import ZipFile
from flask import send_file
from flask_login import current_user
from survey_system.services.form_getter_service import FormVersionGetterService, FormGetterService
import config
import copy

class PaygOpsPackageExporter:

    @classmethod
    def export_form_version(cls, version):
        # Get serialized form data
        form_data = version.get_serialized_object(for_export=True)
        return cls._create_package_file(
            [('create_form_versions', form_data)],
            f"{version.form.name} - v{version.version}",
            f"This package contains the form {version.form.name} v{version.version}."
        )

    @classmethod
    def export_user_journey_version(cls, version):
        # Get serialized journey data
        journey_data = version.get_serialized_object(for_export=True)
        journey_data = copy.deepcopy(journey_data) # This is critical to avoid messing up the journey data
        
        # Initialize list of objects to package with the journey itself
        package_objects = []
        
        # Track processed form IDs to avoid duplicates and their mapping to template IDs
        processed_form_ids = {}
        
        # Track processed automation UUIDs to avoid duplicates and their mapping to template IDs
        processed_automation_uuids = {}
        
        # Find all form steps and collect their form versions
        for step in journey_data.get('steps', []):
            if step.get('type') == 'form':
                form_id = step['data']['form_id']
                if form_id and form_id not in processed_form_ids:
                    form = FormGetterService.get_from_user_and_id(current_user, form_id, strict=True)
                    if form:
                        form_version = FormVersionGetterService.get_from_user_and_id(current_user, form.last_version.id, strict=True)
                        form_data = form_version.get_serialized_object(for_export=True)
                        package_objects.append(('create_form_versions', form_data))
                        processed_form_ids[form_id] = f's{len(package_objects)}'  # Map original ID to position
            # Check for workflow steps with automations
            elif step.get('type') == 'workflow':
                if step['data'].get('workflow_type') == 'automation' and step['data'].get('automation_uuid'):
                    automation_uuid = step['data']['automation_uuid']
                    if automation_uuid and automation_uuid not in processed_automation_uuids:
                        from app_builder_system.automations.models.automation_model import Automation
                        automation = Automation.get(uuid=automation_uuid)
                        if automation:
                            automation_data = cls._get_exported_automation_data(automation)
                            package_objects.append(('create_automations', automation_data))
                            processed_automation_uuids[automation_uuid] = f's{len(package_objects)}'  # Map original UUID to position
            # We also postprocess the button references
            for button in step.get('data', {}).get('buttons', []):
                if button.get('step_id'):
                    del button['step_id']
        
        # Replace form IDs in journey steps with template IDs
        for step in journey_data.get('steps', []):
            if step['type'] == 'form' and step['data']['form_id'] in processed_form_ids:
                step['data']['form_id'] = f"{{{{{processed_form_ids[step['data']['form_id']]}.form_id}}}}"
            # Replace automation UUIDs with template references
            elif step['type'] == 'workflow' and step['data'].get('workflow_type') == 'automation':
                automation_uuid = step['data'].get('automation_uuid')
                if automation_uuid in processed_automation_uuids:
                    step['data']['automation_uuid'] = f"{{{{{processed_automation_uuids[automation_uuid]}.uuid}}}}"
        
        # Add the journey itself to the package
        package_objects.append(('create_user_journey_versions', journey_data))
        
        return cls._create_package_file(
            package_objects,
            f"{version.userjourney.name} - v{version.version}",
            f"This package contains the user journey {version.userjourney.name} v{version.version} and its associated forms and automations."
        )

    @classmethod
    def _get_exported_automation_data(cls, automation):
        automation_data = automation.get_serialized_object(for_export=True)
        automation_data['workflow'] = '{% raw %}' + json.dumps(automation_data['workflow']) + '{% endraw %}'
        return automation_data
    
    @classmethod
    def export_automation(cls, automation):
        # Get serialized automation data
        automation_data = cls._get_exported_automation_data(automation)
        
        return cls._create_package_file(
            [('create_automations', automation_data)],
            f"Automation - {automation.name}",
            f"This package contains the automation {automation.name}."
        )

    @classmethod
    def _create_package_file(cls, objects, package_name, description=None):
        # Create ZIP file in memory
        mem_zip = BytesIO()
        
        with ZipFile(mem_zip, 'w') as zf:
            index = 1
            # We iterate over the objects in the package
            for package_object in objects:
                action, data = package_object
                # Add form JSON file
                object_json = json.dumps(data, indent=2, cls=CustomJSONEncoder)
                object_filename = f"s{index}-{action}.json"
                zf.writestr(object_filename, object_json)
                index += 1
                
            # Add manifest JSON file
            manifest = {
                "name": package_name,
                "description": description,
                "software": "paygops"
            }
            if config.VERSION not in ['local', 'NA']:
                manifest['minimum_version'] = config.VERSION
            manifest_json = json.dumps(manifest, indent=2)
            zf.writestr("manifest.json", manifest_json)
        
        
        # Generate and send the ZIP file
        mem_zip.seek(0)
        return send_file(
            mem_zip,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"{package_name}.pgapp"
        )
