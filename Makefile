INDEX_URL ?= https://pypi.python.org/simple/

PLONE ?= plone52
PYTHON ?= python3
BUILDOUT_CFG ?= test_$(PLONE).cfg
BUILDOUT_ARGS ?= -N
PYBOT_ARGS ?=

.PHONY: all
all: .installed.cfg

nix-%: $(NETRC)
	nix-shell setup.nix -A develop \
	--argstr plone $(PLONE) --argstr python $(PYTHON) \
	--run "$(MAKE) $*"

.PHONY: nix-shell
nix-shell:
	nix-shell setup.nix -A develop \
	--argstr plone $(PLONE) --argstr python $(PYTHON)

build: env

.PHONY: check
check: .installed.cfg
ifeq ($(PYTHON), python3)
	black -t py27 -t py36 -t py37 --check src
	pylama src tests
endif

.PHONY: clean
clean:
	rm -rf .installed bin develop-eggs parts

.PHONY: deploy
deploy: dist
	@echo "Not implemented"

.PHONY: dist
dist:
	@echo "Not implemented"

.PHONY: docs
docs: .installed.cfg
	bin/pocompile src
	LANGUAGE=fi bin/sphinx-build docs html

env:
	nix-build setup.nix -A env \
	--argstr plone $(PLONE) --argstr python $(PYTHON) -o env

.PHONY: format
format: .installed.cfg
ifeq ($(PYTHON), python3)
	black -t py27 src
endif
	bin/isort -rc -y src

.PHONY: serve
serve: .installed.cfg
	bin/instance fg

.PHONY: show
show:
	buildout -c $(BUILDOUT_CFG) $(BUILDOUT_ARGS) annotate

.PHONY: test
test: check
	bin/pocompile src
	bin/test --all
#	LANGUAGE=fi bin/pybot $(PYBOT_ARGS) -d parts/test docs

.PHONY: watch
watch: .installed.cfg
	RELOAD_PATH=src bin/instance fg

.PHONY: robot
robot: .installed.cfg
	bin/robot -d parts/test docs

.PHONY: robot-server
robot-server: .installed.cfg
	LANGUAGE=fi RELOAD_PATH=src \
	bin/robot-server plone.scim.testing.SCIM_ACCEPTANCE_TESTING -v

.PHONY: sphinx
sphinx: .installed.cfg
	bin/robot-sphinx-build -d html docs html

###

.installed.cfg: $(wildcard *.cfg)
	buildout -c $(BUILDOUT_CFG) $(BUILDOUT_ARGS)

requirements-$(PLONE)-$(PYTHON).txt: BUILDOUT_ARGS=-n buildout:overwrite-requirements-file=true buildout:dump-requirements-file=requirements-$(PLONE)-$(PYTHON).txt
requirements-$(PLONE)-$(PYTHON).txt: requirements-buildout.nix
	nix-shell setup.nix -A develop \
	--argstr plone $(PLONE) --argstr python $(PYTHON) \
	--arg requirements ./requirements-buildout.nix  \
	--run "buildout -c $(BUILDOUT_CFG) $(BUILDOUT_ARGS)"

requirements: requirements-$(PLONE)-$(PYTHON).nix
requirements-$(PLONE)-$(PYTHON).nix: requirements-$(PLONE)-$(PYTHON).txt requirements-buildout.txt
	nix-shell --pure -p cacert libffi nix \
	--run 'nix-shell setup.nix -A pip2nix \
	--argstr plone $(PLONE) --argstr python $(PYTHON) \
	--run "pip2nix generate -r requirements-$(PLONE)-$(PYTHON).txt -r requirements-buildout.txt \
	--index-url $(INDEX_URL) \
	--output=requirements-$(PLONE)-$(PYTHON).nix"'

requirements-buildout.nix: requirements-buildout.txt
	nix-shell -p libffi nix \
	--run 'nix-shell setup.nix -A pip2nix \
	--run "pip2nix generate -r requirements-buildout.txt \
	--output=requirements-buildout.nix"'

.PHONY: freeze
freeze:
	@grep "name" requirements.nix |grep -Eo "\"(.*)\""|grep -Eo "[^\"]+"|sed -r "s|-([0-9\.]+)|==\1|g"|grep -v "setuptools="

.PHONY: freeze-buildout
freeze-buildout:
	@grep "name" requirements-buildout.nix |grep -Eo "\"(.*)\""|grep -Eo "[^\"]+"|sed -r "s|-([0-9\.]+)|==\1|g"|grep -v "setuptools="

.PHONY: setup.nix
setup.nix:
	@echo "Updating nixpkgs/nixos-19.03 revision"; \
	rev=$$(curl https://api.github.com/repos/NixOS/nixpkgs-channels/branches/nixos-19.03|jq -r .commit.sha); \
	echo "Updating nixpkgs $$rev hash"; \
	sha=$$(nix-prefetch-url --unpack https://github.com/NixOS/nixpkgs-channels/archive/$$rev.tar.gz); \
	sed -i "2s|.*|    url = \"https://github.com/NixOS/nixpkgs-channels/archive/$$rev.tar.gz\";|" setup.nix; \
	sed -i "3s|.*|    sha256 = \"$$sha\";|" setup.nix;
	@echo "Updating setup.nix revision"; \
	rev=$$(curl https://api.github.com/repos/datakurre/setup.nix/branches/master|jq -r ".commit.sha"); \
	echo "Updating setup.nix $$rev hash"; \
	sha=$$(nix-prefetch-url --unpack https://github.com/datakurre/setup.nix/archive/$$rev.tar.gz); \
	sed -i "6s|.*|    url = \"https://github.com/datakurre/setup.nix/archive/$$rev.tar.gz\";|" setup.nix; \
	sed -i "7s|.*|    sha256 = \"$$sha\";|" setup.nix

.PHONY: upgrade
upgrade:
	nix-shell --pure -p cacert curl gnumake jq nix --run "make setup.nix"
