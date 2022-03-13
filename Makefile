.PHONY: install test dev clean doc check check-format format lint

DEV_BUILD_FLAG = .venv/DEV_BUILD_FLAG
LINT_PATH = gitlogfeed.py

install:
	python3 setup.py install

check: check-format lint

dev: $(DEV_BUILD_FLAG)

$(DEV_BUILD_FLAG):
	python -m venv .venv
	.venv/bin/pip install black==22.1.0 pylint
	touch $(DEV_BUILD_FLAG)

clean:
	-rm -rf .venv

format: $(DEV_BUILD_FLAG)
	.venv/bin/black $(LINT_PATH) 

check-format: $(DEV_BUILD_FLAG)
	.venv/bin/black --check $(LINT_PATH)

lint: $(DEV_BUILD_FLAG)
	.venv/bin/pylint \
		--disable missing-function-docstring \
		--disable missing-class-docstring \
		--disable missing-module-docstring \
		--disable too-few-public-methods \
		$(LINT_PATH)

