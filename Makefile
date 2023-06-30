.PHONY: check
check:
	$(RM) CHANGES.rst
	# run the test suite
	# tox -e test
	# get a coverage report
	# tox -e coverage
	# check if the package is ready to be released
	tox -e release-check
	# check if the dependencies are all specified
	tox -e dependencies
	# generate a dependency graph
	tox -e dependencies-graph
	# check if there are circular dependencies
	tox -e circular
	# format the code
	tox -e format
	# run all sorts of QA tools (code smells, typo finder...)
	tox -e lint

.PHONY: format
format:
	tox -e format

.PHONY: shell
shell:
	devenv shell

###

nix-%:
	nix develop --command $(MAKE) $*
