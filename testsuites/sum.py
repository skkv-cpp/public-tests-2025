import os

import testsuites.suite as suite

from typing import Iterable, Tuple, List, Dict, Optional, Union

SUITE_NAME = "sum"
SUITE_DIR = suite.make_suite_dirname(SUITE_NAME)

class __Comparator(suite.Comparator):
	def __init__(self):
		super().__init__()

	def test(self, user_process: suite.UserProcess, test: suite.Test) -> suite.Result:
		# Sum's output file.
		output_filename = str(list(test.input)[1])

		# Sum's expected output file.
		expected_filename = str(test.expected)

		# Check, if file exists.
		if not os.path.exists(output_filename):
			return suite.err_file_not_found(output_filename)

		# Read files.
		actual_stream = open(output_filename, "r")
		expected_stream = open(expected_filename, "r")
		actual_lines = actual_stream.readlines()
		expected_lines = expected_stream.readlines()

		# Check, if number of lines is equals.
		actual_lines_len = len(actual_lines)
		expected_lines_len = len(expected_lines)
		if actual_lines_len != expected_lines_len:
			return suite.err_assertion_len(actual_lines_len, expected_lines_len)

		# Check contents. As we know, that expected has only two lines (first - is answer, second - is newline), then we should just compare first line as ints.
		actual = int(actual_lines[0])
		expected = int(expected_lines[0])
		if actual != expected:
			return suite.Result(suite.Errno.ERROR_ASSERTION, f"wrong sum, expected '{expected}', but actual is '{actual}'")

		# Otherwise, test is success.
		return suite.err_ok()

def __test_naming(a: Union[int, str], b: Union[int, str], is_file: bool = True) -> str:
	if is_file:
		return f"test_{a}_{b}"
	return f"{a} + {b}"

def __file_naming(a: Union[int, str], b: Union[int, str], suffix: str) -> str:
	return f"{__test_naming(a, b)}.{suffix}"

def __file_dir_naming(a: Union[int, str], b: Union[int, str], suffix: str) -> str:
	suitename = __file_naming(a, b, suffix)
	return os.path.join(SUITE_DIR, suitename)

def __generate_tests() -> Iterable[Tuple[str, List[str], str, str]]:
	paths = [suite.TESTDATA_DIR, SUITE_DIR]

	for p in paths:
		if os.path.exists(p) and not os.path.isdir(p):
			raise ValueError(f"[FATAL ERROR] Provided path '{p}' should be directory.")

		if not os.path.exists(p):
			os.mkdir(p)

	generated: Iterable[Tuple[str, List[str], str, str]]= []

	for a in range(1, 10):
		for b in range(10, 20):
			name = __test_naming(a, b, False)
			raw_input = __file_dir_naming(a, b, "in")
			raw_output = __file_dir_naming(a, b, "out")
			raw_expected = __file_dir_naming(a, b, "ref")
			with open(raw_input, "w") as stream:
				stream.write(f"{a} {b}\n")
			if os.path.exists(raw_output):
				os.remove(raw_output)
			with open(raw_expected, "w") as stream:
				stream.write(f"{a + b}\n")
			test_data = (name, [raw_input, raw_output], raw_output, raw_expected)
			generated.append(test_data)

	return generated

def __error_handling_tests() -> Iterable[Tuple[str, List[str]]]:
	tests = []

	tests.append(("no arguments", []))
	tests.append(("only one argument", ["just_imagine_there_is_second_filename.txt"]))
	tests.append(("no file", ["input.txt", "output.txt"]))

	raw_input = __file_dir_naming("x", "y", "in")
	raw_output = __file_dir_naming("x", "y", "out")
	with open(raw_input, "w") as stream:
		stream.write("x y\n")
	tests.append(("X Y", [raw_input, raw_output]))

	return tests

def get_instance() -> Tuple[suite.Tester, Optional[Dict[str, float]]]:
	COEFF_TO_ENVNAME = {
		"a + b": "A_PLUS_B",
		"bad sum": "BAD_SUM"
	}

	cmp = __Comparator()
	tester = suite.Tester(
		comparator = cmp,
		is_stdin_input = False,
		is_raw_input = True,
		is_raw_output = False
	)
	coefficients = suite.get_coefficients(SUITE_NAME, COEFF_TO_ENVNAME)

	tests = __generate_tests()
	for test_data in tests:
		test_name, test_input, test_output_stream, test_expected = test_data
		tester.add_success(test_name, test_input, test_expected, test_output_stream, categories = ["a + b"])

	ERROR_EXITCODE = 1
	tests = __error_handling_tests()
	for test_data in tests:
		test_name, test_input = test_data
		tester.add_failed(test_name, test_input, ERROR_EXITCODE, categories = ["bad sum"])

	return tester, coefficients
