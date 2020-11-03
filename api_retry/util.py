# standard libraries
import json, logging
from json.decoder import JSONDecodeError
from typing import Any, Dict, Union

# third-party libraries
from requests import Response
from umich_api.api_utils import ApiUtil


LOGGER = logging.getLogger(__name__)


def check_if_response_successful(response: Response) -> bool:
    """
    Checks whether response has 200 status code and the JSON text can be parsed.

    :param response: Response from ApiUtil.api_call
    :type response: Response
    :return: True or False depending on whether the response was successful
    :rtype: bool
    """
    response_successful: bool = True

    status_code: int = response.status_code
    if status_code != 200:
        LOGGER.warning(f'Received irregular status code: {status_code}')
        response_successful = False
    else:
        try:
            json.loads(response.text)
        except JSONDecodeError:
            LOGGER.warning('JSONDecodeError encountered')
            response_successful = False

    if not response_successful:
        LOGGER.warning(response.text)
    return response_successful


def api_call_with_retries(
    api_handler: ApiUtil,
    url: str,
    subscription: str,
    method: str,
    payload: Union[Dict[str, Any], None] = None,
    max_req_attempts: int = 3,
) -> Union[Response, None]:
    """
    Pulls data from the UM API Directory, handling errors and retrying if necessary.

    When the maximum number of request attempts is reached, the function logs an error and returns None.
    :param api_handler: Instance of ApiUtil
    :type api_handler: ApiUtil
    :param url: URL ending for request
    :type url: string
    :param subscription: Name of the subscription or scope the request should use
    :type subscription: string
    :param method: Request method that should be used (e.g. "GET", "PUT")
    :type method: string
    :param payload: Dictionary to include in the request body
    :type payload: Dictionary with string keys or None, optional
    :param max_req_attempts: Number of request attempts to make before logging an error
    :type max_req_attempts: int, optional
    :return: Either a Response object or None
    :rtype: Response or None
    """
    if payload is None:
        request_payload = dict()
    else:
        request_payload = payload

    LOGGER.debug('Making a request for data...')

    for i in range(1, max_req_attempts + 1):
        LOGGER.debug(f'Attempt #{i}')
        response = api_handler.api_call(url, subscription, method, request_payload)
        LOGGER.debug(f'Response URL: {response.url}')

        if not check_if_response_successful(response):
            LOGGER.info('Beginning next_attempt')
        else:
            return response

    LOGGER.error('The maximum number of request attempts was reached; returning None')
    return None
