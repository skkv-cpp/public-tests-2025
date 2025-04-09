import os

import testsuites.suite as suite

import pygraphviz as pgv

from typing import Iterable, Tuple, List, Dict, Optional, Union

SUITE_NAME = "libs"
SUITE_DIR = suite.make_suite_dirname(SUITE_NAME)

__OUTPATH = os.path.join(SUITE_DIR, "out")

class __BadComparator(suite.Comparator):
	def __init__(self):
		super().__init__()

	def test(self, _: suite.UserProcess, test: suite.Test) -> suite.Result:
		# Input file.
		file_that_should_not_be_created = str(list(test.input)[1])

		# If file exists, then test is failed.
		if os.path.exists(file_that_should_not_be_created):
			return suite.err_file_created_on_error(file_that_should_not_be_created)

		return suite.err_ok()

class __Comparator(suite.Comparator):
	def __init__(self):
		super().__init__()

	def test(self, _: suite.UserProcess, test: suite.Test) -> suite.Result:
		# Sum's output file.
		act_file = str(list(test.input)[1])

		# Sum's expected output file.
		exp_file = str(test.expected)

		# Check, if file exists.
		if not os.path.exists(act_file):
			return suite.err_file_not_found(act_file)

		# Any exception should be as "bad RBTree".
		try:
			# Assert
			verdict = True

			g_exp = pgv.AGraph(exp_file)
			g_act = pgv.AGraph(act_file)

			verdict = verdict and (g_exp.number_of_edges() == g_act.number_of_edges()) and (g_exp.number_of_nodes() == g_act.number_of_nodes())

			g_exp_nodes = sorted(g_exp.nodes())
			g_act_nodes = sorted(g_act.nodes())
			attr_check = True
			for i in range(len(g_exp_nodes)):
				g_exp_ni_successors = sorted(g_exp.successors(g_exp_nodes[i]))
				g_act_ni_successors = sorted(g_act.successors(g_act_nodes[i]))
				attr_check = attr_check and (g_exp_nodes[i].attr == g_act_nodes[i].attr) and (g_exp_ni_successors == g_act_ni_successors)

			verdict = verdict and attr_check

			g_exp_edges = sorted(g_exp.edges())
			g_act_edges = sorted(g_act.edges())
			attr_check = True
			for i in range(len(g_exp_edges)):
				attr_check = attr_check and (g_exp_edges[i].attr == g_act_edges[i].attr)
			verdict = verdict and attr_check

			# If verdict is False, then there is bad invariant.
			# Otherwise, test is success.
			if verdict:
				return suite.err_ok()
			else:
				return suite.Result(suite.Errno.ERROR_ASSERTION, "wrong invariant")
		except Exception as e:
			return suite.Result(suite.Errno.ERROR_ASSERTION, f"bad RBTree: {str(e)}")

def __neg(i: int) -> str:
	return os.path.join(__OUTPATH, f"neg{i}.dot")

def __file_test(i: int, is_input: bool = True) -> str:
	prefix = "in" if is_input else "out"
	return f"{prefix}{i}.dot"

def __file(i: int, is_input: bool = True) -> str:
	return os.path.join(SUITE_DIR, __file_test(i, is_input))

def __out(i: int) -> str:
	return os.path.join(__OUTPATH, f"out{i}.dot")

def __generate_tests() -> Iterable[Tuple[str, List[str], str, str]]:
	if os.path.exists(__OUTPATH) and not os.path.isdir(__OUTPATH):
		raise ValueError(f"[FATAL ERROR] Provided path '{__OUTPATH}' should be directory.")

	if not os.path.exists(__OUTPATH):
		os.mkdir(__OUTPATH)

	generated: List[Tuple[str, List[str], str, str]] = []

	for i in range(0, 5):
		name = f"RBTree #{i + 1}"
		raw_input = __file(i, True)
		raw_output = __out(i)
		raw_expected = __file(i, False)
		test_data = (name, [raw_input, raw_output], raw_output, raw_expected)
		generated.append(test_data)

	return generated

def __error_handling_tests() -> Iterable[Tuple[str, List[str], Optional[suite.Comparator]]]:
	tests: List[Tuple[str, List[str], Optional[suite.Comparator]]] = []

	cmp = __BadComparator()
	tests.append(("no arguments", [], None))
	tests.append(("only one argument", ["Is this the real life? Is this just fantasy?"], None))
	tests.append(("no files", ["Caught_in_a_landslide.dot", "no_escape_from_reality.dot"], cmp))
	tests.append(("wrong number of arguments", ["Open", "your", "eyes", ",", "look", "up", "to", "the", "skies", "and", "see"], cmp))

	raw_input = __neg(0)
	raw_output = "this_file_should_not_be_created.dot"
	tests.append(("bad graph", [raw_input, raw_output], cmp))

	return tests

def get_instance() -> Tuple[suite.Tester, Optional[Dict[str, float]]]:
	COEFF_TO_ENVNAME = {
		"positive": "POSITIVE",
		"neg": "NEG"
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
		tester.add_success(test_name, test_input, test_expected, test_output_stream, categories = ["positive"])

	ERROR_EXITCODE = 1
	tests = __error_handling_tests()
	for test_data in tests:
		test_name, test_input, test_comparator = test_data
		tester.add_failed(test_name, test_input, ERROR_EXITCODE, categories = ["neg"], comparator = test_comparator)

	return tester, coefficients
