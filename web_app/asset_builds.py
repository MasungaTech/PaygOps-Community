from flask_assets import Environment, Bundle
import config

ASSET_BUILDS = {
    'css': {
        'vendor': ['vendor/css/core-light.css',
                 'vendor/css/theme-semi-dark-light.css'],  
        'libs': ['libs/perfect-scrollbar/perfect-scrollbar.css',
                 'libs/toastr/toastr.css', 
                 'libs/select2/select2.css',
                 'libs/flatpickr/flatpickr.css',
                 'libs/tagify/tagify.css',
                 'libs/bs-stepper/bs-stepper.css'],
        'custom': ['custom/css/custom-core.css']
    },
    'js': {
        'vendor': ['vendor/js/helpers.js',
                 'libs/jquery/jquery.js'],
        'core': ['libs/jquery/jquery.validate.min.js',
                 'libs/jquery/jquery.serializejson.min.js', 
                 'libs/toastr/toastr.js',
                 'vendor/js/menu.js',
                    'vendor/js/dropdown-hover.js',
                    'vendor/js/cards-actions.js',
                    'vendor/js/autosize.js'],
        'libs': ['libs/perfect-scrollbar/perfect-scrollbar.js', 
                 'libs/select2/select2.js',
                 'libs/flatpickr/flatpickr.js',
                 'libs/sortablejs/sortable.js',
                 'libs/tagify/tagify.js',
                 'custom/js/flatpickr.lng.js'],
        'libs_extra': ['js/sorttable.v2.js',
                       'js/pagination.min.js',
                       'js/JIC.js',
                       'js/ExifRestorer.js',
                       'js/signature_pad.min.js'],
        'custom': ['custom/js/picture_upload.js',
                   'custom/js/phone_edit.js',
                   'custom/js/main.js',
                   'custom/js/colors.js',
                   'custom/js/helpers.js',
                   'js/paginatetable.v2.js',
                   'js/add_remove_buttons.js',
                   'js/tags.js',
                   'custom/js/icon_picker.js']
    }
}

ENTERPRISE_ASSETS = {
    'js': {
        'custom': ['/crm/task_system/web_app/static/task_system.js']
    }
}

def register_assets(assets, app_config=None):
    build_assets(assets, 'css', 'cssutils', app_config)
    build_assets(assets, 'js', 'rjsmin', app_config)
    build_language_files()


def build_assets(assets, type, filter, app_config=None):
    for build in ASSET_BUILDS[type]:
        asset_list = list(ASSET_BUILDS[type][build])
        asset_list = ['/crm/web_app/static/'+p for p in asset_list]
        if config.ENABLE_ENTERPRISE_FEATURES:
            asset_list += ENTERPRISE_ASSETS.get(type, {}).get(build, [])
        bundle_name = build+'.'+type
        bundle = Bundle(asset_list, filters=filter, output='assets_cache/'+bundle_name)
        assets.register(build+'_'+type, bundle)
        bundle.build()
        bundle_hash = bundle._env.manifest.query(bundle, bundle._env)
        if not 'webassets_hashes' in app_config:
            app_config['webassets_hashes'] = {}
        app_config['webassets_hashes'][bundle_name] = bundle_hash


def build_language_files():
    import config
    from shared.services.translation_service import TranslationService
    for language in config.AVAILABLE_WEB_LANGUAGES:
        if language not in ['XX']:
            content = TranslationService.get_js_language_file_content(language)
            language = language.lower()
            file = open(config.WEB_STATIC_PATH+f'assets_cache/paygops.lng.{language}.js', 'w+')
            file.write(content)
            file.close()