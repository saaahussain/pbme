.PHONY: test demo eval benchmark broker-benchmark reports

test:
	PYTHONPATH=src python -m pytest -q

demo:
	PYTHONPATH=src python -m pbme.demo

eval:
	PYTHONPATH=src python -m pbme.evaluation

benchmark:
	PYTHONPATH=src python -m pbme.benchmark.cli run --repeats 3

broker-benchmark:
	PYTHONPATH=src python -m pbme.benchmark.cli broker-run --repeats 3

reports:
	PYTHONPATH=src python -m pbme.benchmark.cli report
