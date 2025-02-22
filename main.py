#!/usr/bin/env python3

import argparse
import os
import json

from typing import Dict, Tuple, Optional

import testsuites.suite as suite
import testsuites.sum as suite_sum

SELECTOR: Dict[str, Tuple[suite.Tester, Optional[Dict[str, float]]]] = {
	suite_sum.SUITE_NAME: suite_sum.get_instance(),
}

def __calculate_final_sum(results: suite.Suite, coefficients: Optional[Dict[str, float]]) -> float:
	if coefficients is None or len(coefficients) == 0:
		return 0.0
	f_sum = 0.0
	raw_results = results.get_results()
	for category, coefficient in coefficients.items():
		if category not in raw_results:
			return 0.0
		raw = raw_results[category]
		f_sum += coefficient * raw
	return f_sum

if __name__ == "__main__":
	# Arguments.
	parser = argparse.ArgumentParser()
	parser.add_argument("--program", help = "path to the program under test", type = str, required = True)
	parser.add_argument("--suite", help = "select testing task", type = str, choices = SELECTOR, required = True)
	parser.add_argument("--timeout-factor", help = "maximum execution time multiplier", type = float, default = 1.0)
	parser.add_argument("--json-output-name", help = "generate full JSON report with provided output filename", type = str, default = None)

	# Parse from sys.argv.
	args = vars(parser.parse_args())

	# suite arguments.
	suite_program = os.path.abspath(args["program"])
	suite_suite = str(args["suite"])

	# Test setup.
	setup_timeout_factor: float = float(args["timeout_factor"])

	# JSON results.
	json_output_name = args["json_output_name"]

	task_select, coefficients = SELECTOR[suite_suite]
	results = task_select.run(suite_program, setup_timeout_factor)
	exitcode = 0 if results.ok() else 1

	json_final_sum = __calculate_final_sum(results, coefficients)

	if json_output_name is not None:
		json_full_dict: Dict[str, dict] = dict()

		json_full_dict["exitcode"] = exitcode
		json_full_dict["result"] = json_final_sum
		json_full_dict["results"] = results.get_results()
		json_full_dict.update(results.json())

		json_object = json.dumps(json_full_dict, indent = 4)

		with open(json_output_name, "w") as stream:
			stream.write(json_object)

		print(f"-- JSON reported in {json_output_name}")

	exit(exitcode)
