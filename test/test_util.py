# standard libraries
import logging, random
from typing import List

# third-party libraries
from django.test import TestCase

# local libraries
from pe.models import Exam, Submission
from util import chunk_list


LOGGER = logging.getLogger(__name__)


class ChunkingTestCase(TestCase):
    fixtures: List[str] = ['test_01.json', 'test_04.json']

    def test_chunk_list_of_random_nums_with_default_size_and_multiple_chunks(self):
        """
        chunk_list creates a list of three integer lists of lengths 100, 100, and 50 with default chunk_size.
        """
        random_nums: List[int] = random.sample(range(1000000), 250)
        result: List[List[int]] = chunk_list(random_nums)

        self.assertEqual(len(result), 3)
        self.assertEqual(len(result[0]), 100)
        self.assertEqual(len(result[1]), 100)
        self.assertEqual(len(result[2]), 50)

        all_nums: List[int] = [random_num for sublist in result for random_num in sublist]
        self.assertEqual(random_nums, all_nums)

    def test_chunk_list_of_random_nums_with_default_size_and_less_than_one_chunk(self):
        """
        chunk_list creates a list containing one element, also a list, when input length is less than chunk_size.
        """
        random_nums: List[int] = random.sample(range(1000000), 70)
        result: List[List[int]] = chunk_list(random_nums)

        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0]), 70)
        self.assertEqual(result[0], random_nums)

    def test_chunk_list_of_subs_with_custom_size_and_more_than_one_chunk(self):
        """
        chunk_list chunks a list of three submissions into a list of two lists with lengths 2 and 1 when chunk_size is 2.
        """
        submissions: List[Submission] = list(Exam.objects.get(id=1).submissions.all())
        result: List[List[Submission]] = chunk_list(submissions, chunk_size=2)

        self.assertEqual(len(result), 2)
        self.assertEqual(len(result[0]), 2)
        self.assertEqual(len(result[1]), 1)

        all_subs: List[Submission] = [submission for sublist in result for submission in sublist]
        self.assertEqual(submissions, all_subs)
