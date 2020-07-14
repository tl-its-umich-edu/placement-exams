# standard libraries
import logging
from typing import Any, List

LOGGER = logging.getLogger(__name__)


def chunk_list(input_list: List[Any], chunk_size: int = 100):
    """Chunks a given list into a list of lists of a specified size."""
    chunks = [input_list[x:x + chunk_size] for x in range(0, len(input_list), chunk_size)]
    LOGGER.debug(chunks)
    return chunks
