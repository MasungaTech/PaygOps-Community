import json
from shared.api_helpers.server_helpers.jwt_and_schema_verification import validate_schema
from shared.services.ai_completion_service import AICompletionService
from shared.logger.loggers import Error

class AIOfferCreationService:

    OPENAPI_SPEC = """
    ```json
    "requestBody": {
        "description": "Offer Model with at least the required properties.<br>",
        "content": {
            "application/json": {
                "schema": {
                    "oneOf": [
                    {
                        "type": "object",
                        "properties": {
                        "based_on": {
                            "oneOf": [
                            { "type": "integer" },
                            { "type": "string", "pattern": "^[-+]?[0-9]+$" },
                            { "type": "string", "maxLength": 0 },
                            { "type": "null" }
                            ],
                            "example": 123,
                            "description": "If the offer is a new version of an existing offer"
                        },
                        "name": { "type": "string", "example": "My offer", "description": "Descriptive name of the offer, in form of a short text" },
                        "code": { "type": "string", "example": "MY_OFFER_CODE", "description": "Unique code to identify the offer, cannot contain spaces" },
                        "type": { "type": "string", "description": "Discriminator propertiy that defines the rest of the properties being sent/expected", "const": "Loan", "example": "Loan" },
                        "linked_to_product": { "type": "boolean", "example": true, "description": "Defines whether the offer should be tied to a device or not" },
                        "can_be_approved_and_registered": { "type": "boolean", "example": true, "description": "Defines whether the leads can be registered under this offer" },
                        "in_use_for_new_leads": { "type": "boolean", "example": true, "description": "Defines whether this offer can be assigned to new leads" },
                        "approval_required": { "type": "boolean", "example": true, "description": "Defines whether this leads with this offer need to be approved or not" },
                        "device_type": { "oneOf": [ { "type": "string" }, { "type": "null" } ], "example": "NPG", "description": "Restrict the offer to only one specific device type, so leads under this offer cannot be registered with devices of other device type" },
                        "lighting_global_compliant": { "type": "boolean", "example": true, "description": "Establish wether this offer is compliant with Lighting Global Standards" },
                        "panel_size_in_w": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 5.0, "description": "The size of the panels in W (if applicable)" },
                        "raw_unit_cost": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 5.0, "description": "The raw cost if the device" },
                        "battery_size_in_ah": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 5.0, "description": "The battery size of the device (if applicable)" },
                        "family": { "type": "string", "enum": ["Home", "Business"], "example": "Home", "description": "Whether the consumer is a home or a business" },
                        "product_sub_type_id": { "description": "The ID of the product sub-type to which this offer is restricted to, if applicable", "oneOf": [ { "type": "integer" }, { "type": "string", "pattern": "^[-+]?[0-9]+$" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 123 },
                        "notes": { "type": "string", "example": "My extra info about the offer", "description": "Additional notes on the offer" },
                        "offline_token_config": { "example": {}, "description": "Configuration for offline token" },
                        "base_price_amount_can_be_negative": { "type": "boolean", "example": true, "description": "Allows negative base price amount" },
                        "add_allowed_addon_offer_categories_ids": { "type": "array", "items": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+$" }, { "type": "integer" } ] }, "example": [1, 2, 3], "description": "The list of ids to add to the allowed Add-ons categories" },
                        "add_entities_allowed_for_leads_ids": { "type": "array", "items": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+$" }, { "type": "integer" } ] }, "example": [1, 2, 3], "description": "The list of ids to add to the Operational Entities allowed for sales" },
                        "add_entities_allowed_for_contracts_ids": { "type": "array", "items": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+$" }, { "type": "integer" } ] }, "example": [1, 2, 3], "description": "The list of ids to add to the Operational Entities allowed for registration" },
                        "time_to_ownership_in_days": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 200.0, "description": "Total time duration of the contract if paid using the reference pricing" },
                        "automatic_unlock_code_sending": { "type": "boolean", "example": true, "description": "Weather to automatically unlock the device forever when finishing contract" },
                        "allow_loan_addons": { "type": "boolean", "example": true, "description": "Weather loans addons are allowed or not" },
                        "maximum_value_extension": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 200.0, "description": "The maximum allowed value of loan extension with loan extension add-ons. " },
                        "downpayment": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 10.0, "description": "The amount to be paid as registration fee, before registration" },
                        "base_price_amount": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" } ], "example": 10, "description": "The reference amount to be paid in each payment/installment" },
                        "discount_price_1_amount": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 20.0, "description": "Amount above which the 1st discounted pricing applies" },
                        "discount_price_2_amount": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 30.0, "description": "Amount above which the 2st discounted pricing applies" },
                        "minimum_payment": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 9.0, "description": "Minimuma amount accepted to generate a repayment in the contract (and activate device if applicable)" },
                        "base_price_time_in_days": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 10.0, "description": "Time period equivalent to the reference amount" },
                        "discount_price_1_time_in_days": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 22.0, "description": "Time period equivalent to the 1st discounted pricing amount" },
                        "discount_price_2_time_in_days": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 26.0, "description": "Time period equivalent to the 2st discounted pricing amount" },
                        "time_given_at_start_in_days": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 5.0, "description": "Time period given at the beggining of the contract (equivalent to the downpayment amount)" },
                        "allow_pro_rata": { "type": "boolean", "default": true, "example": true, "description": "Defines whether this offer allows payments for arbitrary amounts (higher than the minimum), if true, or only the exact reference/discounted pricing amounts (if false)" },
                        "forgive_lateness": { "type": "boolean", "default": true, "example": true, "description": "Defines whether this offer forgives late payments, adding the credit from now (if true) or adding the time from the time when the activation time expired (if false)" }
                        },
                        "additionalProperties": false,
                        "required": ["name", "code", "type", "approval_required", "family", "can_be_approved_and_registered", "in_use_for_new_leads", "linked_to_product", "downpayment", "base_price_amount", "time_to_ownership_in_days", "automatic_unlock_code_sending", "base_price_time_in_days", "time_given_at_start_in_days"],
                        "title": "Loan Offer"
                    },
                    {
                        "type": "object",
                        "properties": {
                        "based_on": {
                            "oneOf": [
                            { "type": "integer" },
                            { "type": "string", "pattern": "^[-+]?[0-9]+$" },
                            { "type": "string", "maxLength": 0 },
                            { "type": "null" }
                            ],
                            "example": 123,
                            "description": "If the offer is a new version of an existing offer"
                        },
                        "name": { "type": "string", "example": "My offer", "description": "Descriptive name of the offer, in form of a short text" },
                        "code": { "type": "string", "example": "MY_OFFER_CODE", "description": "Unique code to identify the offer, cannot contain spaces" },
                        "type": { "type": "string", "description": "Discriminator propertiy that defines the rest of the properties being sent/expected", "const": "Lump Sum", "example": "Lump Sum" },
                        "linked_to_product": { "type": "boolean", "example": true, "description": "Defines whether the offer should be tied to a device or not" },
                        "can_be_approved_and_registered": { "type": "boolean", "example": true, "description": "Defines whether the leads can be registered under this offer" },
                        "in_use_for_new_leads": { "type": "boolean", "example": true, "description": "Defines whether this offer can be assigned to new leads" },
                        "approval_required": { "type": "boolean", "example": true, "description": "Defines whether this leads with this offer need to be approved or not" },
                        "device_type": { "oneOf": [ { "type": "string" }, { "type": "null" } ], "example": "NPG", "description": "Restrict the offer to only one specific device type, so leads under this offer cannot be registered with devices of other device type" },
                        "lighting_global_compliant": { "type": "boolean", "example": true, "description": "Establish wether this offer is compliant with Lighting Global Standards" },
                        "panel_size_in_w": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 5.0, "description": "The size of the panels in W (if applicable)" },
                        "raw_unit_cost": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 5.0, "description": "The raw cost if the device" },
                        "battery_size_in_ah": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 5.0, "description": "The battery size of the device (if applicable)" },
                        "family": { "type": "string", "enum": ["Home", "Business"], "example": "Home", "description": "Whether the consumer is a home or a business" },
                        "product_sub_type_id": { "description": "The ID of the product sub-type to which this offer is restricted to, if applicable", "oneOf": [ { "type": "integer" }, { "type": "string", "pattern": "^[-+]?[0-9]+$" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 123 },
                        "notes": { "type": "string", "example": "My extra info about the offer", "description": "Additional notes on the offer" },
                        "offline_token_config": { "example": {}, "description": "Configuration for offline token" },
                        "base_price_amount_can_be_negative": { "type": "boolean", "example": true, "description": "Allows negative base price amount" },
                        "add_allowed_addon_offer_categories_ids": { "type": "array", "items": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+$" }, { "type": "integer" } ] }, "example": [1, 2, 3], "description": "The list of ids to add to the allowed Add-ons categories" },
                        "add_entities_allowed_for_leads_ids": { "type": "array", "items": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+$" }, { "type": "integer" } ] }, "example": [1, 2, 3], "description": "The list of ids to add to the Operational Entities allowed for sales" },
                        "add_entities_allowed_for_contracts_ids": { "type": "array", "items": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+$" }, { "type": "integer" } ] }, "example": [1, 2, 3], "description": "The list of ids to add to the Operational Entities allowed for registration" },
                        "base_price_amount_lump_sum": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" } ], "example": 100.0, "description": "Total price of the offer" }
                        },
                        "additionalProperties": false,
                        "required": ["name", "code", "type", "approval_required", "family", "can_be_approved_and_registered", "in_use_for_new_leads", "linked_to_product", "base_price_amount_lump_sum"],
                        "title": "Lump-sum Offer"
                    },
                    {
                        "type": "object",
                        "properties": {
                        "based_on": {
                            "oneOf": [
                            { "type": "integer" },
                            { "type": "string", "pattern": "^[-+]?[0-9]+$" },
                            { "type": "string", "maxLength": 0 },
                            { "type": "null" }
                            ],
                            "example": 123,
                            "description": "If the offer is a new version of an existing offer"
                        },
                        "name": { "type": "string", "example": "My offer", "description": "Descriptive name of the offer, in form of a short text" },
                        "code": { "type": "string", "example": "MY_OFFER_CODE", "description": "Unique code to identify the offer, cannot contain spaces" },
                        "type": { "type": "string", "description": "Discriminator propertiy that defines the rest of the properties being sent/expected", "const": "Time Based", "example": "Time Based" },
                        "linked_to_product": { "type": "boolean", "example": true, "description": "Defines whether the offer should be tied to a device or not" },
                        "can_be_approved_and_registered": { "type": "boolean", "example": true, "description": "Defines whether the leads can be registered under this offer" },
                        "in_use_for_new_leads": { "type": "boolean", "example": true, "description": "Defines whether this offer can be assigned to new leads" },
                        "approval_required": { "type": "boolean", "example": true, "description": "Defines whether this leads with this offer need to be approved or not" },
                        "device_type": { "oneOf": [ { "type": "string" }, { "type": "null" } ], "example": "NPG", "description": "Restrict the offer to only one specific device type, so leads under this offer cannot be registered with devices of other device type" },
                        "lighting_global_compliant": { "type": "boolean", "example": true, "description": "Establish wether this offer is compliant with Lighting Global Standards" },
                        "panel_size_in_w": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 5.0, "description": "The size of the panels in W (if applicable)" },
                        "raw_unit_cost": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 5.0, "description": "The raw cost if the device" },
                        "battery_size_in_ah": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 5.0, "description": "The battery size of the device (if applicable)" },
                        "family": { "type": "string", "enum": ["Home", "Business"], "example": "Home", "description": "Whether the consumer is a home or a business" },
                        "product_sub_type_id": { "description": "The ID of the product sub-type to which this offer is restricted to, if applicable", "oneOf": [ { "type": "integer" }, { "type": "string", "pattern": "^[-+]?[0-9]+$" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 123 },
                        "notes": { "type": "string", "example": "My extra info about the offer", "description": "Additional notes on the offer" },
                        "offline_token_config": { "example": {}, "description": "Configuration for offline token" },
                        "base_price_amount_can_be_negative": { "type": "boolean", "example": true, "description": "Allows negative base price amount" },
                        "add_allowed_addon_offer_categories_ids": { "type": "array", "items": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+$" }, { "type": "integer" } ] }, "example": [1, 2, 3], "description": "The list of ids to add to the allowed Add-ons categories" },
                        "add_entities_allowed_for_leads_ids": { "type": "array", "items": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+$" }, { "type": "integer" } ] }, "example": [1, 2, 3], "description": "The list of ids to add to the Operational Entities allowed for sales" },
                        "add_entities_allowed_for_contracts_ids": { "type": "array", "items": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+$" }, { "type": "integer" } ] }, "example": [1, 2, 3], "description": "The list of ids to add to the Operational Entities allowed for registration" },
                        "payment_frequency": { "type": "string", "enum": ["DAILY", "MONTHLY"], "description": "Whether the payments schedule will be defined in natural months or in days" },
                        "base_price_time_in_months": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 1, "description": "Time period equivalent to the reference amount (to be used only if `payment_frequency` is monthly)" },
                        "discount_price_1_time_in_months": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 1, "description": "Time period equivalent to the 1st discounted pricing amount (to be used only if `payment_frequency` is monthly)" },
                        "discount_price_2_time_in_months": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 2, "description": "Time period equivalent to the 2st discounted pricing amount (to be used only if `payment_frequency` is monthly)" },
                        "time_given_at_start_in_months": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 1, "description": "Time period given at the beggining of the contract (equivalent to the downpayment amount) in months (to be used only if `payment_frequency` is monthly)" },
                        "payment_day_of_month": { "oneOf": [ { "type": "integer" }, { "type": "string", "pattern": "^[-+]?[0-9]+$" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 5, "description": "The day of the month on which the payment is due" },
                        "downpayment": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 10.0, "description": "The amount to be paid as registration fee, before registration" },
                        "base_price_amount": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" } ], "example": 10, "description": "The reference amount to be paid in each payment/installment" },
                        "discount_price_1_amount": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 20.0, "description": "Amount above which the 1st discounted pricing applies" },
                        "discount_price_2_amount": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 30.0, "description": "Amount above which the 2st discounted pricing applies" },
                        "minimum_payment": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 9.0, "description": "Minimuma amount accepted to generate a repayment in the contract (and activate device if applicable)" },
                        "base_price_time_in_days": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 10.0, "description": "Time period equivalent to the reference amount" },
                        "discount_price_1_time_in_days": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 22.0, "description": "Time period equivalent to the 1st discounted pricing amount" },
                        "discount_price_2_time_in_days": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 26.0, "description": "Time period equivalent to the 2st discounted pricing amount" },
                        "time_given_at_start_in_days": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 5.0, "description": "Time period given at the beggining of the contract (equivalent to the downpayment amount)" },
                        "allow_pro_rata": { "type": "boolean", "default": true, "example": true, "description": "Defines whether this offer allows payments for arbitrary amounts (higher than the minimum), if true, or only the exact reference/discounted pricing amounts (if false)" },
                        "forgive_lateness": { "type": "boolean", "default": true, "example": true, "description": "Defines whether this offer forgives late payments, adding the credit from now (if true) or adding the time from the time when the activation time expired (if false)" }
                        },
                        "additionalProperties": false,
                        "required": ["name", "code", "type", "approval_required", "family", "can_be_approved_and_registered", "in_use_for_new_leads", "linked_to_product", "downpayment", "base_price_amount"],
                        "title": "Time Based Offer"
                    },
                    {
                        "type": "object",
                        "properties": {
                        "based_on": {
                            "oneOf": [
                            { "type": "integer" },
                            { "type": "string", "pattern": "^[-+]?[0-9]+$" },
                            { "type": "string", "maxLength": 0 },
                            { "type": "null" }
                            ],
                            "example": 123,
                            "description": "If the offer is a new version of an existing offer"
                        },
                        "name": { "type": "string", "example": "My offer", "description": "Descriptive name of the offer, in form of a short text" },
                        "code": { "type": "string", "example": "MY_OFFER_CODE", "description": "Unique code to identify the offer, cannot contain spaces" },
                        "type": { "type": "string", "description": "Discriminator propertiy that defines the rest of the properties being sent/expected", "const": "Usage Based", "example": "Usage Based" },
                        "linked_to_product": { "type": "boolean", "example": true, "description": "Defines whether the offer should be tied to a device or not" },
                        "can_be_approved_and_registered": { "type": "boolean", "example": true, "description": "Defines whether the leads can be registered under this offer" },
                        "in_use_for_new_leads": { "type": "boolean", "example": true, "description": "Defines whether this offer can be assigned to new leads" },
                        "approval_required": { "type": "boolean", "example": true, "description": "Defines whether this leads with this offer need to be approved or not" },
                        "device_type": { "oneOf": [ { "type": "string" }, { "type": "null" } ], "example": "NPG", "description": "Restrict the offer to only one specific device type, so leads under this offer cannot be registered with devices of other device type" },
                        "lighting_global_compliant": { "type": "boolean", "example": true, "description": "Establish wether this offer is compliant with Lighting Global Standards" },
                        "panel_size_in_w": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 5.0, "description": "The size of the panels in W (if applicable)" },
                        "raw_unit_cost": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 5.0, "description": "The raw cost if the device" },
                        "battery_size_in_ah": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 5.0, "description": "The battery size of the device (if applicable)" },
                        "family": { "type": "string", "enum": ["Home", "Business"], "example": "Home", "description": "Whether the consumer is a home or a business" },
                        "product_sub_type_id": { "description": "The ID of the product sub-type to which this offer is restricted to, if applicable", "oneOf": [ { "type": "integer" }, { "type": "string", "pattern": "^[-+]?[0-9]+$" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 123 },
                        "notes": { "type": "string", "example": "My extra info about the offer", "description": "Additional notes on the offer" },
                        "offline_token_config": { "example": {}, "description": "Configuration for offline token" },
                        "base_price_amount_can_be_negative": { "type": "boolean", "example": true, "description": "Allows negative base price amount" },
                        "add_allowed_addon_offer_categories_ids": { "type": "array", "items": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+$" }, { "type": "integer" } ] }, "example": [1, 2, 3], "description": "The list of ids to add to the allowed Add-ons categories" },
                        "add_entities_allowed_for_leads_ids": { "type": "array", "items": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+$" }, { "type": "integer" } ] }, "example": [1, 2, 3], "description": "The list of ids to add to the Operational Entities allowed for sales" },
                        "add_entities_allowed_for_contracts_ids": { "type": "array", "items": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+$" }, { "type": "integer" } ] }, "example": [1, 2, 3], "description": "The list of ids to add to the Operational Entities allowed for registration" },
                        "downpayment": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 10.0, "description": "The amount to be paid as registration fee, before registration" },
                        "allow_pro_rata": { "type": "boolean", "default": true, "example": true, "description": "Defines whether this offer allows payments for arbitrary amounts (higher than the minimum), if true, or only the exact reference/discounted pricing amounts (if false)" },
                        "minimum_payment": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 9.0, "description": "Minimuma amount accepted to generate a repayment in the contract (and activate device if applicable)" },
                        "free_credit_at_start_usage_based": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 10.0, "description": "Credit given at the beggining of the contract (equivalent to the downpayment amount)" },
                        "credit_unit": { "type": "string", "example": "Liters", "description": "Credit units in which the offer is based" },
                        "base_price_amount": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" } ], "example": 10, "description": "The reference amount to be paid" },
                        "base_price_credit_in_units": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 1, "description": "Amount if units equivalent to the reference amount" },
                        "discount_price_1_amount": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 20.0, "description": "Amount above which the 1st discounted pricing applies" },
                        "discount_price_1_credit_in_units": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 2, "description": "Amount if units equivalent to `discount_price_1_amount`" },
                        "discount_price_1_time_in_days": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 3, "deprecated": true, "description": "Amount if units equivalent to `discount_price_2_amount`" },
                        "discount_price_2_amount": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 30.0, "description": "Amount above which the 2st discounted pricing applies" },
                        "discount_price_2_credit_in_units": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 3, "description": "Amount if units equivalent to `discount_price_2_amount`" },
                        "discount_price_2_time_in_days": { "oneOf": [ { "type": "string", "pattern": "^[-+]?[0-9]+\\.?[0-9]*$" }, { "type": "number", "format": "float" }, { "type": "string", "maxLength": 0 }, { "type": "null" } ], "example": 3, "deprecated": true, "description": "Amount if units equivalent to `discount_price_2_amount`" }
                        },
                        "additionalProperties": false,
                        "required": ["name", "code", "type", "approval_required", "family", "can_be_approved_and_registered", "in_use_for_new_leads", "linked_to_product", "downpayment", "free_credit_at_start_usage_based", "credit_unit", "base_price_amount", "base_price_credit_in_units", "discount_price_1_amount", "discount_price_1_credit_in_units", "discount_price_2_amount", "discount_price_2_credit_in_units"],
                        "title": "Usage Based Offer"
                    }
                    ]
                }
        }
    }
    ```
    """

    BASE_PROMPT = BASE_PROMPT = """
    Based on the JSON schema provided below, create an offer for a <<user_input>>

    Important Instructions:
        - If the offer type is "Loan", the total loan value excludes the value of the free days given at start, you MUST adjust the base price to take that into account.
        - For Loan, triple check that the total loan value = (reference pricing amount / reference pricing duration in days) * (days to ownership - free days given at start) + downpayment amount
        - If the offer type is "Time Based" (i.e. a subscription), you must include the `payment_frequency` field.
        include:
        - `base_price_time_in_days`
        - `time_given_at_start_in_days`

    JSON Schema:
    """ + OPENAPI_SPEC


    FIX_PROMPT = """Based on the JSON schema provided below, create an offer for a <<user_input>>

        Important Instructions:
        - If the offer type is "Time Based" (i.e. a subscription), you must include the `payment_frequency` field.
        include:
        - `base_price_time_in_days`
        - `time_given_at_start_in_days`

        The previous JSON output was:
        ```json
            <<ai_generated_output>>

            The validation error is:
            ```
            <<validation_error>>
            ```
            JSON Schema:
            """+OPENAPI_SPEC+"""
        Please fix the JSON to ensure it adheres to the OpenAPI specification and resolves the validation error. Only output the corrected JSON payload.
    """

    @classmethod
    def create_offer(cls, prompt, name, user):
        from payg_loan_system.offers.services.create_offer_service import CreateOfferService
        from payg_loan_system.offers.models import Offer
        max_retries = 2
        attempt = 0
        cleaned_output = None

        while attempt < max_retries:
            try:
                # Generate the initial output or retry with fixed JSON
                if cleaned_output is None:
                    ai_generated_output = AICompletionService.get_completion(
                        cls.BASE_PROMPT, prompt_user_inputs={"user_input": prompt}
                    )
                    cleaned_output = cls.clean_ai_generated_output(ai_generated_output)
                else:
                    print(f"Retrying with corrected JSON... Attempt {attempt + 1}")
                
                # Parse the JSON and validate it
                offer_data = json.loads(cleaned_output)
                validation_schema = Offer.get_model_schema(op='create', for_validate=True)
                validate_schema(offer_data, validation_schema)
                
                # Update required fields
                offer_data['name'] = name
                offer_data['can_be_approved_and_registered'] = True
                offer_data['in_use_for_new_leads'] = True

                # Process the offer
                offer = CreateOfferService.add_from_data_and_user(user=user, data=offer_data)
                return offer

            except Exception as e:
                # Log the error and try fixing the JSON
                print(f"Validation failed on attempt {attempt + 1}: {str(e)}")
                cleaned_output = cls.fix_json_with_ai(cleaned_output, str(e), prompt)
                attempt += 1
        
        # If all attempts fail, raise a ValueError
        raise Error(f"The prompt:  {prompt} given does not make sense and cannot produce valid JSON. fails with Error: {str(cleaned_output)}")

    
    @classmethod
    def clean_ai_generated_output(cls, ai_generated_output):
        if '```json' in ai_generated_output:
            ai_generated_output = ai_generated_output.split('```json')[1]
        if '```' in ai_generated_output:
            ai_generated_output = ai_generated_output.split('```')[0]
        return ai_generated_output
    
    
    @classmethod
    def fix_json_with_ai(cls, ai_generated_output, validation_error, prompt):
        """
        Prompt the AI to fix the JSON based on the validation error, using `custom_format` for safe formatting.
        """
        # Use custom_format to safely insert JSON and error message into the prompt
        fix_prompt = AICompletionService.custom_format(
            cls.FIX_PROMPT, 
            {"user_input": prompt, "ai_generated_output": ai_generated_output, "validation_error": validation_error}
        )
        
        # Call AI to generate a fixed JSON
        fixed_output = AICompletionService.get_completion(fix_prompt)
        return cls.clean_ai_generated_output(fixed_output)