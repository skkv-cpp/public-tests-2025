import os
import shutil
import numpy as np

import testsuites.suite as suite

from enum import Enum
from typing import Tuple, Optional, Dict, Iterable, List, Union

SUITE_NAME = "invmat"
__SUITE_DIR = suite.make_suite_dirname(SUITE_NAME)

# (<subdir name>, <file ext>)
class __TestType(Enum):
	IN = ("in", "in")
	OUT = ("out", "out")
	REF = ("ref", "out")

# 'no solution' comparator.
class __NoSolutionComparator(suite.Comparator):
	def __init__(self):
		super().__init__()

	def test(self, _: suite.UserProcess, test: suite.Test) -> suite.Result:
		# No solution's output file.
		output_filename = str(list(test.input)[1])

		# No solution's expected output file.
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

		# Check contents. As we know, that expected has only two lines (first - is answer, second - is newline), then we should just check, if first line is "no solution".
		actual = actual_lines[0]
		expected = expected_lines[0]
		if actual != expected:
			return suite.Result(suite.Errno.ERROR_ASSERTION, f"wrong verdict, expected '{suite.escape(expected)}', but actual is '{suite.escape(actual)}'")

		# Otherwise, test is success.
		return suite.err_ok()

# Actual vs. expected matrix comparator.
class __GoodComparator(suite.Comparator):
	def __init__(self):
		super().__init__()

	def test(self, _: suite.UserProcess, test: suite.Test) -> suite.Result:
		# Constants.
		DELTA = 1e-4

		# Actual's output file.
		output_filename = str(list(test.input)[1])

		# Expected's expected output file.
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

		# Comparison header.
		out_header = actual_lines[0]
		ref_header = expected_lines[0]
		r = 0
		c = 0
		try:
			out_r, out_c = map(int, out_header.split(' '))
			ref_r, ref_c = map(int, ref_header.split(' '))
			if out_r != ref_r or out_c != ref_c:
				return suite.Result(
							suite.Errno.ERROR_ASSERTION,
							what = f"expected matrix size ({ref_r}x{ref_c}) is not equals to actual ({out_r}x{out_c})"
				)
			r = ref_r
			c = ref_c
		except ValueError:
			return suite.Result(suite.Errno.ERROR_TYPE_ERROR, what = "R/C should be integers")

		# Comparison matrices.
		nested_actual_matrix = [s.strip().split(' ') for s in actual_lines[1:]]
		nested_expected_matrix = [s.strip().split(' ') for s in expected_lines[1:]]

		for i in range(r):
			if len(nested_actual_matrix[i]) != len(nested_expected_matrix[i]):
				return suite.Result(
					suite.Errno.ERROR_ASSERTION,
					what = f"expected number of columns {len(nested_expected_matrix[i])} on row #{i} is not equals to actual ({len(nested_actual_matrix[i])})"
				)

		actual_matrix = np.array([[float(j) for j in i] for i in nested_actual_matrix])
		expected_matrix = np.array([[float(j) for j in i] for i in nested_expected_matrix])

		max_abs = np.fmax(np.abs(expected_matrix), np.abs(actual_matrix))
		max_by_row = np.amax(max_abs, axis = 1)
		max_by_col = np.amax(max_abs, axis = 0)

		for y in range(r):
			for x in range(c):
				a = actual_matrix[y][x]
				e = expected_matrix[y][x]
				diff = abs(a - e)
				m = min(max_by_row[y], max_by_col[x])
				d = diff / m
				if d > DELTA:
					return suite.Result(
						suite.Errno.ERROR_ASSERTION,
						what = f"at (row, column)=({y}, {x}) position should be {float(e)} (+/-{DELTA}), but found {float(a)}"
					)

		# Otherwise, test is success.
		return suite.err_ok()

def __make_basename(type: __TestType, name: Union[int, str]) -> str:
	return "test_%s.%s" % (str(name), type.value[1])

def __make_categorized_basename(category: str, type: __TestType, name: Union[int, str]) -> str:
	return os.path.join(category.replace(" ", "_"), __make_basename(name, type))

def __make_subdir_basename(category: str, type: __TestType, name: Optional[Union[int, str]] = None) -> str:
	if name is None:
		return os.path.join(type.value[0], category.replace(' ', '_'))
	else:
		return os.path.join(type.value[0], __make_categorized_basename(category, name, type))

def __make_in_basename(category: str, name: Optional[Union[int, str]] = None) -> str:
	return __make_subdir_basename(category, __TestType.IN, name)

def __make_out_basename(category: str, name: Optional[Union[int, str]] = None) -> str:
	return __make_subdir_basename(category, __TestType.OUT, name)

def __make_ref_basename(category: str, name: Optional[Union[int, str]] = None) -> str:
	return __make_subdir_basename(category, __TestType.REF, name)

def __make_in_path(category: str, name: Optional[Union[int, str]] = None) -> str:
	return os.path.join(__SUITE_DIR, __make_in_basename(category, name))

def __make_out_path(category: str, name: Optional[Union[int, str]] = None) -> str:
	return os.path.join(__SUITE_DIR, __make_out_basename(category, name))

def __make_ref_path(category: str, name: Optional[Union[int, str]] = None) -> str:
	return os.path.join(__SUITE_DIR, __make_ref_basename(category, name))

def __write_mtx(mtx, filename: str, fmt: str = "%g"):
	rows, cols = mtx.shape
	with open(filename, 'w') as f:
		f.write(f"{rows} {cols}\n")
		np.savetxt(f, mtx, fmt = fmt)

def __read_mtx(filename: str, dtype = float):
	with open(filename, "r") as f:
		_, cols = f.readline().split()
	m_n = range(int(cols))
	m = np.loadtxt(filename, dtype = dtype, delimiter = " ", skiprows = 1, usecols = (m_n), ndmin = 2)
	return m

def __create_test_files(test_case: str, test_idx: int, mtx, fmt: str = "%g") -> Tuple[str, str, str]:
	input_mtx_file = __make_in_path(test_case, test_idx)
	__write_mtx(mtx, input_mtx_file, fmt = fmt)
	ref_mtx_file = __make_ref_path(test_case, test_idx)
	inverted_mtx = np.linalg.inv(__read_mtx(input_mtx_file))
	__write_mtx(inverted_mtx, ref_mtx_file, fmt = fmt)
	return input_mtx_file, __make_out_path(test_case, test_idx), ref_mtx_file

def __cleanup(path: str):
	if os.path.exists(path):
		shutil.rmtree(path)
	suite.ensure_existence_directory(path)

def __full_cleanup(category: str):
	__cleanup(__make_in_path(category))
	__cleanup(__make_ref_path(category))
	__cleanup(__make_out_path(category))

def __generate_bad_tests() -> Iterable[Tuple[str, str, str, int]]:
	generated: List[Tuple[str, str, str, int]] = []

	category = "neg"

	empty_file_raw_input = __make_in_path(category, 1)
	with open(empty_file_raw_input, "w") as file:
		file.write('\n')
	test_data = ("Empty file", category, empty_file_raw_input, 1)
	generated.append(test_data)

	return generated

def __generate_good_tests() -> Iterable[Tuple[str, str, str, str, str, Optional[suite.Comparator]]]:
	generated: List[Tuple[str, str, str, str, str, Optional[suite.Comparator]]] = []

	category = "eye"
	__full_cleanup(category)
	sizes_1 = [5]
	for i in range(len(sizes_1)):
		m = np.eye(sizes_1[i])
		raw_input, raw_output, raw_expected = __create_test_files(category, i, m)
		test_data = (f"{category.capitalize()} #{i}", category, raw_input, raw_output, raw_expected, None)
		generated.append(test_data)

	category = "diag"
	__full_cleanup(category)
	sizes_2 = [23]
	for i in range(len(sizes_2)):
		m = np.eye(sizes_2[i])
		for j in range(sizes_2[i]):
			m[j][j] = np.random.randint(-100, 100)
			if m[j][j] == 0:
				m[j][j] = 1
		raw_input, raw_output, raw_expected = __create_test_files(category, i, m)
		test_data = (f"{category.capitalize()} #{i}", category, raw_input, raw_output, raw_expected, None)
		generated.append(test_data)

	category = "normal"
	__full_cleanup(category)
	sizes_3 = [7, 11]
	for i in range(len(sizes_3)):
		m = np.zeros((sizes_3[i], sizes_3[i]))
		while np.linalg.det(m) == 0:
			for j in range(sizes_3[i]):
				for k in range(sizes_3[i]):
					m[j][k] = np.random.randint(-100, 100)
		raw_input, raw_output, raw_expected = __create_test_files(category, i, m)
		test_data = (f"{category.capitalize()} #{i}", category, raw_input, raw_output, raw_expected, None)
		generated.append(test_data)

	category = "neg"
	__full_cleanup(category)
	neg_mtx = [
		np.array([[-76, 98]]),
		np.zeros((20, 20))
	]
	cmp = __NoSolutionComparator()
	for i, m in enumerate(neg_mtx):
		raw_input = __make_in_path(category, i + 2)
		raw_output = __make_out_path(category, i + 2)
		raw_expected = __make_ref_path(category, i + 2)
		__write_mtx(m, raw_input)
		with open(raw_expected, "w") as file:
			file.write("no_solution\n")
		test_data = (f"{category.capitalize()} #{i + 2}", category, raw_input, raw_output, raw_expected, cmp)
		generated.append(test_data)

	return generated

def get_instance() -> Tuple[suite.Tester, Optional[Dict[str, float]]]:
	COEFF_TO_ENVNAME = {
		"eye": "EYE",
		"diag": "DIAG",
		"normal": "NORMAL",
		"neg": "NEG"
	} 
	TIMEOUT = 0.5

	np.random.seed(225526)

	cmp = __GoodComparator()
	tester = suite.Tester(
		comparator = cmp,
		is_stdin_input = False,
		is_raw_input = True,
		is_raw_output = False
	)
	coefficients = suite.get_coefficients(SUITE_NAME, COEFF_TO_ENVNAME)

	good_tests = __generate_good_tests()
	bad_tests = __generate_bad_tests()

	for test_data in good_tests:
		test_name, test_category, test_input, test_output, test_expected, test_comparator = test_data
		tester.add_success(test_name, [test_input, test_output], test_expected, test_output, categories = [test_category], comparator = test_comparator, timeout = TIMEOUT)

	for test_data in bad_tests:
		test_name, test_category, test_input, test_exitcode = test_data
		tester.add_failed(test_name, [test_input, "non_existing.out"], test_exitcode, timeout = TIMEOUT, categories = [test_category])

	return tester, coefficients
