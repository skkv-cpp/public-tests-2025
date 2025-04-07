import os
import subprocess
import time

from enum import Enum
from typing import Any, List, Union, Tuple, Optional, Dict, Iterable, Set
from abc import abstractmethod, ABC

TESTDATA_DIR = "testdata"

class Errno(Enum):
	ERROR_SUCCESS = "success"
	ERROR_SHOULD_PASS = "program should not fail"
	ERROR_SHOULD_FAIL = "program should not return successful exitcode"
	ERROR_STDERR_EMPTY = "standard error output is empty"
	ERROR_STDOUT_NOT_EMPTY = "on error program should not writing anything to standard output"
	ERROR_STDERR_NOT_EMPTY = "on successful program should not writing anything to standard error output"
	ERROR_EXITCODE = "program returns wrong exitcode"
	ERROR_ASSERTION = "assertion"
	ERROR_TIMEOUT = "timeout expired"
	ERROR_FILE_NOT_FOUND = "file not found"
	ERROR_FILE_CREATED_ON_ERROR = "file was created (as empty or with undefined state) after failing"
	ERROR_FILE_RECREATED_ON_ERROR = "file was recreated (as empty or with undefined state) after failing"
	ERROR_TYPE_ERROR = "type casting error"
	ERROR_NO_NEWLINE = "no newline at EOF"
	ERROR_UNKNOWN = "unknown"

class UserProcess:
	def __init__(self, stdout: str, stderr: str, exitcode: Optional[int], timestamp: int):
		self.stdout = stdout
		self.stderr = stderr
		self.exitcode = exitcode
		self.timestamp = timestamp

	def timeout(self) -> bool:
		return self.exitcode == None

class Result:
	def __init__(self, errno: Errno, what: Optional[str] = None):
		self.__errno = errno
		self.__what = what

	def ok(self) -> bool:
		return self.__errno == Errno.ERROR_SUCCESS

	def get_verdict(self) -> str:
		return self.__errno.value

	def get_additional_info(self) -> Optional[str]:
		return self.__what

	def __str__(self) -> str:
		if self.__what is None:
			return f"   Verdict: {self.__errno.value}."
		else:
			return f"   Verdict: {self.__errno.value}.\n   Additional information: {self.__what}."

	def ok(self) -> bool:
		return self.__errno == Errno.ERROR_SUCCESS

def suite_to_dirname(suite: str) -> str:
	# All directories should have `_` instead of `-`.
	return suite.replace("-", "_")

def ensure_existence_directory(dirname: str):
	# Check if it's exists, otherwise create parent.
	if not os.path.exists(dirname):
		ensure_existence_directory(os.path.abspath(os.path.join(dirname, os.pardir)))

	# Check if it is directory, otherwise - it's fatal error.
	if os.path.exists(dirname) and os.path.isfile(dirname):
		raise ValueError(f"[FATAL ERROR] Provided path '{os.path.abspath(dirname)}' should be directory.")

	# Create directory.
	if not os.path.exists(dirname):
		os.mkdir(dirname)

def make_suite_dirname(suite: str) -> str:
	ensure_existence_directory(TESTDATA_DIR)
	p = os.path.join(TESTDATA_DIR, suite_to_dirname(suite))
	ensure_existence_directory(p)
	return p

def get_coefficients(suite_name: str, envnames: Dict[str, str]) -> Optional[Dict[str, float]]:
	PREFIX = "SKKV_CPP"
	coefficients: Dict[str, float] = {}
	categories: List[str] = list(envnames.keys())
	for category in categories:
		raw_value = os.getenv(f"{PREFIX}_{suite_name.upper()}_{envnames[category]}")
		if raw_value is None:
			return None
		coefficients[category] = float(raw_value)
	return coefficients

def escape(x: str) -> str:
	s = ""
	for c in x:
		if c == "\n":
			s += "\\n"
		elif c == "\r":
			s += "\\r"
		elif c == "\t":
			s += "\\t"
		elif c == "\\":
			s += "\\\\"
		else:
			s += c
	return s

def to_list(input: Union[str, int, float, List[str], List[int], List[float]], need_newline: bool = True) -> List[str]:
	if isinstance(input, (str, int, float)):
		l = [str(input)]
		if need_newline:
			l.append("")
		return l
	elif isinstance(input, list):
		l = [str(item) for item in input]
		if need_newline:
			l.append("")
		return l
	else:
		raise TypeError("[FATAL ERROR] Input must be a string, integer, float, or a list of strings, integers, or floats.")

def to_str(input: Union[str, int, float, List[str], List[int], List[float]], separator: str = "") -> str:
	if isinstance(input, (str, int, float)):
		return str(input)
	elif isinstance(input, list):
		return separator.join([str(item) for item in input])
	else:
		raise TypeError("[FATAL ERROR] Input must be a string, integer, float, or a list of strings, integers, or floats.")

def err_ok() -> Result:
	return Result(Errno.ERROR_SUCCESS)

def err_should_pass(exitcode: int) -> Result:
	return Result(Errno.ERROR_SHOULD_PASS, what = f"program returned exitcode {exitcode}")

def err_should_fail() -> Result:
	return Result(Errno.ERROR_SHOULD_FAIL, what = "program returned exitcode = 0")

def err_stderr_empty() -> Result:
	return Result(Errno.ERROR_STDERR_EMPTY, what = f"program should write any human readable error message for user")

def err_stdout_not_empty(stdout: str) -> Result:
	return Result(Errno.ERROR_STDOUT_NOT_EMPTY, what = f"stdout: '{escape(stdout)}'")

def err_stderr_not_empty(stderr: str) -> Result:
	return Result(Errno.ERROR_STDERR_NOT_EMPTY, what = f"stderr: '{escape(stderr)}'")

def err_exitcode(actual_exitcode: int, expected_exitcode: int) -> Result:
	return Result(Errno.ERROR_EXITCODE, what = f"expected {expected_exitcode}, but actual {actual_exitcode}")

def err_timeout() -> Result:
	return Result(Errno.ERROR_TIMEOUT)

def err_assertion_lines(actual: str, expected: str, lineno: int) -> Result:
	if expected == '':
		return Result(Errno.ERROR_ASSERTION, what = "newline at the end of stream is necessary")
	return Result(Errno.ERROR_ASSERTION, what = f"on output line #{lineno} expected was '{escape(expected)}', but actual is '{escape(actual)}'")

def err_assertion_pos(i: int, j: int, actual: str, expected: str) -> Result:
	return Result(Errno.ERROR_ASSERTION, what = f"at (row, column)=({i}, {j}) position should be '{expected}', but actual is '{actual}'")

def err_assertion_len(actual_len: int, expected_len: int) -> Result:
	return Result(Errno.ERROR_ASSERTION, what = f"the number of rows in the actual solution ({actual_len}) does not match the number of rows in the expected solution ({expected_len})")

def err_file_not_found(file: str) -> Result:
	return Result(Errno.ERROR_FILE_NOT_FOUND, what = f"file '{file}' should be created after running program")

def err_file_created_on_error(file: str) -> Result:
	return Result(Errno.ERROR_FILE_CREATED_ON_ERROR, what = f"file '{file}' should not be created after program's failing")

def err_file_recreated_on_error(file: str) -> Result:
	return Result(Errno.ERROR_FILE_RECREATED_ON_ERROR, what = f"file '{file}' should be same as it was before program's failing")

def err_type_error(i: int, j: int, type_error_message: str) -> Result:
	return Result(Errno.ERROR_TYPE_ERROR, what = f"at (row, column)=({i}, {j}) position should be {type_error_message}")

def err_no_newline() -> Result:
	return Result(Errno.ERROR_NO_NEWLINE)

def err_unknown(what: str) -> Result:
	return Result(Errno.ERROR_UNKNOWN, what = escape(what))

def get_time() -> int:
	return time.time_ns() // 1000000

class Test:
	def __init__(self,
			name: str,
			categories: Iterable[str],
			input: Union[str, int, float, List[str], List[int], List[float]],
			expected: Optional[Union[str, int, float, List[str], List[int], List[float]]],
			output_stream: Optional[str],
			timeout: float,
			exitcode: int,
			is_stdin_input: bool,
			is_raw_input: bool,
			is_raw_output: bool,
			input_separator: str,
			comparator: Optional[Any] = None,
	):
		self.name = name
		self.categories = categories

		self.input = input
		self.expected = expected
		self.__output_stream = output_stream
		self.__timeout = timeout
		self.exitcode = exitcode

		self.__is_stdin_input = is_stdin_input
		self.__is_raw_input = is_raw_input
		self.__is_raw_output = is_raw_output
		self.input_separator = input_separator
		self.comparator = comparator

		self.passes = exitcode == 0

	# Returns None, if there was a timeout expired exception.
	# Otherwise, returns tuple of STDOUT, STDERR and RETURNCODE of program.
	def __runner(self, program: str, input: Union[str, int, float, List[str], List[int], List[float]], timeout: float, timeout_factor: float, wrap: Optional[str]) -> Optional[UserProcess]:
		full_program: List[str] = []
		no_wrap = wrap is None
		if no_wrap:
			full_program = [program]
		else:
			full_program = [wrap, program]
		full_timeout = timeout * timeout_factor

		# If it's not STDIN communication, turn input to list as cmd's arguments.
		if not self.__is_stdin_input:
			full_program += to_list(input, False)

		# If it's STDIN communication, then process should be created and then communicated.
		# Otherwise, run once.
		if self.__is_stdin_input:
			proc = subprocess.Popen(full_program, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE, universal_newlines = True, shell = not no_wrap)
			start = get_time()
			try:
				if self.__is_raw_input:
					stdout, stderr = proc.communicate(to_str(input, self.input_separator), timeout = full_timeout)
					end = get_time()
					return (end - start, (stdout, stderr, proc.returncode))
				else:
					file_content = ""
					if isinstance(input, str):
						with open(input, "r") as stream:
							file_content = stream.read()
					else:
						raise ValueError(f"[FATAL ERROR] When it's stdin communication and not as raw string producer, then it should be path/to/file with wanted contents.")
					stdout, stderr = proc.communicate(file_content, timeout = full_timeout)
					end = get_time()
					return UserProcess(stdout, stderr, proc.returncode, end - start)
			except subprocess.TimeoutExpired:
				proc.kill()
				end = get_time()
				return UserProcess("", "", None, end - start)
		else:
			start = get_time()
			try:
				proc = subprocess.Popen(full_program, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE, universal_newlines = True, shell = not no_wrap)
				stdout, stderr = proc.communicate(timeout = full_timeout)
				end = get_time()
				return UserProcess(stdout, stderr, proc.returncode, end - start)
			except subprocess.TimeoutExpired:
				end = get_time()
				proc.kill()
				return UserProcess("", "", None, end - start)

	def run(self, program: str, timeout_factor: float, wrap: Optional[str]) -> Union[UserProcess, Result]:
		try:
			return self.__runner(program, self.input, self.__timeout, timeout_factor, wrap)
		except Exception as e:
			result = err_unknown(str(e))
			return result

	def get_input(self) -> str:
		input_content = to_str(self.input, " ")
		if not self.__is_raw_input:
			with open(str(self.input), "r") as stream:
				input_content = stream.read()
		return input_content

	def get_reference(self) -> str:
		if self.expected is None:
			return None
		expected_content = to_str(self.expected, " ")
		if not self.__is_raw_output:
			with open(str(self.expected), "r") as file:
				expected_content = file.read()
		return expected_content

class Comparator(ABC):
	def __init__(self):
		pass

	def __should_fail(self, user_process: UserProcess, test: Test) -> Result:
		# Extract user process info.
		stdout = user_process.stdout
		stderr = user_process.stderr
		returncode = user_process.exitcode

		# CASE: Program returns 0.
		if returncode == 0:
			return err_should_fail()

		empty_stderr = stderr == "" or stderr is None
		empty_stdout = stdout == "" or stdout is None

		# CASE: Should be error message.
		if empty_stderr:
			return err_stderr_empty()

		# CASE: Output should be empty.
		if not empty_stdout:
			return err_stdout_not_empty(stdout)

		# CASE: Exitcode must be correct.
		if returncode != test.exitcode:
			# For sanitizers.
			if not empty_stderr:
				print('       STDERR -->')
				print(stderr)
				print('   <-- STDERR')
			return err_exitcode(returncode, test.exitcode)

		return err_ok()

	def __should_pass(self, user_process: UserProcess) -> Optional[Result]:
		# Extract user process info.
		stderr = user_process.stderr
		returncode = user_process.exitcode

		# CASE: Program doesn't returns 0.
		empty_stderr = stderr == "" or stderr is None
		if returncode != 0:
			# For sanitizers.
			if not empty_stderr:
				print('       STDERR -->')
				print(stderr)
				print('   <-- STDERR')
			return err_should_pass(returncode)

		# CASE: Error output should be empty.
		if not empty_stderr:
			return err_stderr_not_empty(stderr)

		# Otherwise, we need abstractic comparing.
		return None

	def pretest(self, user_process: UserProcess, test: Test) -> Optional[Result]:
		if test.passes:
			return self.__should_pass(user_process)
		return self.__should_fail(user_process, test)

	@abstractmethod
	def test(self, user_process: UserProcess, test: Test) -> Result:
		return err_ok()

class Suite:
	def __init__(self):
		self.__results: List[Tuple[Test, Optional[UserProcess], Result]] = []

	def add_result(self, test: Test, user_process: Optional[UserProcess], result: Result):
		self.__results.append((test, user_process, result))

	def ok(self) -> bool:
		return all(result.ok() for _, _, result in self.__results)

	def __get_number_passed(self, category: str) -> int:
		passed = 0
		for results in self.__results:
			test, _, result = results
			if result.ok() and category in test.categories:
				passed += 1
		return passed

	def __get_number_total(self, category: str) -> int:
		total = 0
		for results in self.__results:
			test, _, _ = results
			if category in test.categories:
				total += 1
		return total

	def get_all_categories(self) -> Set[str]:
		all_categories: Set[str] = set()
		for results in self.__results:
			test, _, _ = results
			all_categories.update(test.categories)
		return all_categories

	def get_results(self) -> Dict[str, float]:
		raw: Dict[str, float] = {}
		categories = self.get_all_categories()

		for category in categories:
			passed = self.__get_number_passed(category)
			total = self.__get_number_total(category)
			raw[category] = (passed / total)

		return raw

	def json(self) -> Dict[str, dict]:
		json_results: Dict[str, dict] = {}
		for i, results in enumerate(self.__results):
			test, user_process, result = results
			json_object_name = f"test_{i + 1}"
			json_single_result = {}
			json_single_result["categories"] = list(test.categories)
			json_single_result["passed"] = result.ok()
			json_single_result["verdict"] = result.get_verdict()
			json_single_result["input"] = to_str(test.input, test.input_separator)
			additional_info = result.get_additional_info()
			if additional_info is not None:
				json_single_result["verdict_additional_info"] = additional_info
			json_single_result["name"] = test.name
			if user_process is None:
				json_single_result["stdout"] = "<process was killed>"
				json_single_result["stderr"] = "<process was killed>"
				json_single_result["exitcode"] = "<process was killed>"
				json_single_result["time"] = "<process was killed>"
			else:
				json_single_result["stdout"] = "<no standard output>" if user_process.stdout is None or user_process.stdout == "" else escape(user_process.stdout)
				json_single_result["stderr"] = "<no error output>" if user_process.stderr is None or user_process.stderr == "" else escape(user_process.stderr)
				json_single_result["exitcode"] = "<timeout>" if user_process.exitcode is None else user_process.exitcode
				json_single_result["time"] = user_process.timestamp
			json_results[json_object_name] = json_single_result
		return json_results

class Tester:
	def __init__(self, comparator: Comparator, is_stdin_input: bool = True, is_raw_input: bool = True, is_raw_output: bool = True, input_separator: str = " "):
		self.__comparator = comparator
		self.__is_stdin_input = is_stdin_input
		self.__is_raw_input = is_raw_input
		self.__is_raw_output = is_raw_output
		self.__input_separator = input_separator
		self.__tests: List[Test] = []

		# Not RAW input with not STDIN communication sounds strange.
		if not self.__is_stdin_input and not self.__is_raw_input:
			raise NotImplementedError("[FATAL ERROR] Not raw input (from file) with cmd's arguments communication is not supported yet.")

	def add_success(self, name: str, input: Union[str, int, float, List[str], List[int], List[float]], expected: Union[str, int, float, List[str], List[int], List[float]], output_stream: str = None, timeout: float = 1.0, categories: Iterable[str] = [], comparator: Optional[Comparator] = None):
		test = Test(name, categories, input, expected, output_stream, timeout, 0, self.__is_stdin_input, self.__is_raw_input, self.__is_raw_output, self.__input_separator, comparator)
		self.__tests.append(test)

	def add_failed(self, name: str, input: Union[str, int, float, List[str], List[int], List[float]], exitcode: int, timeout: float = 1.0, categories: Iterable[str] = []):
		test = Test(name, categories, input, None, None, timeout, exitcode, self.__is_stdin_input, self.__is_raw_input, self.__is_raw_output, self.__input_separator)
		self.__tests.append(test)

	def run(self, program: str, timeout_factor: float, wrap: Optional[str]) -> Suite:
		# If there is no file, then no test.
		if not os.path.exists(program):
			raise FileNotFoundError(f"[FATAL ERROR] File (executable) named '{program}' not found.")

		suite = Suite()
		for test in self.__tests:
			print(f"-- Performing {test.name}...")
			result = test.run(program, timeout_factor, wrap)
			# If it's Result, then there was a unknown error.
			if not isinstance(result, Result):
				user_process = result
				# Check, if it was timeout.
				if user_process.timeout():
					result = err_timeout()
					print(result)
					suite.add_result(test, user_process, result)
					continue
				cmp = self.__comparator if test.comparator is None else test.comparator
				result = cmp.pretest(result, test)
				# If real result is None, then pretesting success and we should test with abstract method.
				# Otherwise, pretest is failed.
				result = cmp.test(user_process, test) if result is None else result
				print(result)
				suite.add_result(test, user_process, result)
			else:
				print(result)
				suite.add_result(test, None, result)

		return suite
