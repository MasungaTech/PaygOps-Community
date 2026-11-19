from core_system.users.services.current_user_service import get_current_api_user
from pony.orm import db_session
from shared.api_helpers.documented_resource import DocumentedResource
from shared.api_helpers.server_helpers.jwt_and_schema_verification import verify
from shared.services.settings_service import SettingsService


class McpWriteAccessResource(DocumentedResource):
    """Whether the caller may use MCP write. Does not reveal the setting values."""

    PUBLIC = False

    @verify(permissions=[])
    @db_session
    def get(self):
        user = get_current_api_user()
        return {"allowed": bool(SettingsService.mcp_write_allowed(user))}
