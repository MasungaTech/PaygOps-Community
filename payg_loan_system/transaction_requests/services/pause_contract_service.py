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


class PauseContractTransactionService(TransactionService):

    type = "pause"
    permissions = ["PauseContractActions"]
    description = (
        "Pauses a contract given either by `device_serial` or `contract_reference`"
    )
    schema = {
        "oneOf": [
            {
                "title": "By Device Serial Number",
                "type": "object",
                "properties": {
                    "device_serial": DEVICE_SERIAL_SCHEMA,
                    "note": NOTES_SCHEMA,
                    "send_sms": {
                        **BOOLEAN_SCHEMA,
                        **{'description': "Whether the result of the transaction should be sent to the client to inform about the pause of the contract"}
                    }
                },
                "required": ["device_serial"],
            },
            {
                "title": "By Contract Reference",
                "type": "object",
                "properties": {
                    "contract_reference": CONTRACT_REFERENCE_SCHEMA,
                    "note": NOTES_SCHEMA,
                    "send_sms": {
                        **BOOLEAN_SCHEMA,
                        **{'description': "Whether the result of the transaction should be sent to the client to inform about the pause of the contract"}
                    }
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
        
        return {"contract": contract, "client": contract.client}

    @classmethod
    def _process(cls, user, offline, time, contract, **kwargs):
        send_sms = kwargs.get("send_sms")
        note = kwargs.get("note", "")
        answer = ContractTerminationService.pause_contract(
            contract, user, note=note, send_sms=send_sms
        )
        return answer
