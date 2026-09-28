from web_app import app
import config

if __name__ == '__main__':
    print('Building stuff...')
    app.jinja_env.compile_templates('template_cache')
    from web_app.asset_builds import build_language_files
    build_language_files()