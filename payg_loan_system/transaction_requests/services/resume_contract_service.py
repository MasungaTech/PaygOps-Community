from payg_loan_system.contracts.models.contract_status import ContractStatus
from payg_loan_system.contracts.services.contract_termination_service import (
    ContractTerminationService,
)
from payg_loan_system.transaction_requests.services.transaction_service import (
    BOOLEAN_SCHEMA,
    CONTRACT_REFERENCE_SCHEMA,
    DEVICE_SERIAL_SCHEMA,
    NOTES_SCHEMA,
    TransactionService,
)
from shared.logger.loggers import Error


class ResumeContractTransactionService(TransactionService):

    type = "resume"
    permissions = ["ResumeContractActions"]
    description = (
        "Resumes a contract given either by `device_serial` or `contract_reference`"
    )
    schema = {
        "oneOf": [
            {
                "title": "By Device Serial Number",
                "type": "object",
                "properties": {
                    "device_serial": DEVICE_SERIAL_SCHEMA,
                    "send_sms_to_client": {
                        **BOOLEAN_SCHEMA,
                        **{'description': "Whether the result of the transaction should be sent to the client via SMS"}
                    },
                    "note": NOTES_SCHEMA
                },
                "required": ["device_serial"],
            },
            {
                "title": "By Contract Reference",
                "type": "object",
                "properties": {
                    "contract_reference": CONTRACT_REFERENCE_SCHEMA,
                    "send_sms_to_client": {
                        **BOOLEAN_SCHEMA,
                        **{'description': "Whether the result of the transaction should be sent to the client via SMS"}
                    },
                    "note": NOTES_SCHEMA
                },
                "required": ["contract_reference"],
            },
        ],
    }

    @classmethod
    def _validate_data(cls, **kwargs):
        contract = cls._get_contract(
            device_serial=kwargs.get("device_serial"),
            contract_reference=kwargs.get("contract_reference"),
            user=kwargs["user"],
        )
        if not contract:
            raise Error('INVALID_CONTRACT')
        if contract.status == ContractStatus.completed:
            raise Error('CONTRACT_ALREADY_COMPLETED')
        if contract.status == ContractStatus.defaulted:
            raise Error('CONTRACT_ALREADY_DEFAULTED')
        if contract.status != ContractStatus.paused:
            raise Error('CONTRACT_NOT_PAUSED')
        if contract.status == ContractStatus.cancelled:
            raise Error('CONTRACT_ALREADY_CANCELLED')
        
        return {"contract": contract, "client": contract.client, "note": kwargs.get('note')}

    @classmethod
    def _process(cls, user, offline, time, contract, **kwargs):
        return ContractTerminationService.resume_contract(
            contract, user, note=kwargs.get('note')
        )