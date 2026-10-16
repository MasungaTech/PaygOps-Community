from shared.api_helpers.client_helpers.json_serialization_helpers import deserialize_received_json
from shared.api_helpers.client_helpers.api_exceptions import APIAuthorizationError, APIRemoteServerError, APIResourcePermissionError, APIInvalidInputError


def check_request_status(request_result):
    if request_result.status_code == 200:
        return
    # If it's an error we print extra details
    if request_result.request is not None and request_result.request.body:
        print("Request URL and Body: ", request_result.request.url, request_result.request.body)
    else:
        print("No Request Body")
    if request_result is not None and request_result.text:
        print("Response Status Code and Body: ", request_result.status_code, request_result.text)
    else:
        print("No Response Body")
    if request_result.status_code == 401:
        raise APIAuthorizationError(str(deserialize_received_json(request_result)))
    if request_result.status_code == 403:
        raise APIResourcePermissionError(str(deserialize_received_json(request_result)))
    if request_result.status_code == 500:
        raise APIRemoteServerError(str(deserialize_received_json(request_result)))
    if request_result.status_code == 400:
        raise APIInvalidInputError(deserialize_received_json(request_result))
    request_result.raise_for_status()
