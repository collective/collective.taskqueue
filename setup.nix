{ pkgs ? import (fetchTarball {
    url = "https://github.com/NixOS/nixpkgs-channels/archive/36516712916ebb7475cf3fb5da3a7df6230a60e7.tar.gz";
    sha256 = "1vaqh7i7qd68wkcj8lzjzrv7s5zzpw1lz30r9jr7wf1y2ssikci5";
  }) {}
, setup ? import (fetchTarball {
    url = "https://github.com/datakurre/setup.nix/archive/e835238aed6a0058cf3fd0f3d6ae603532db5cb4.tar.gz";
    sha256 = "0gak3pg5nrrhxj2cws313jz80pmdys047ypnyhagvrfry5a9wa48";
  })
# , setup ? import ../setup.nix
, plone ? "plone52"
, python ? "python3"
, pythonPackages ? builtins.getAttr (python + "Packages") pkgs
, requirements ? ./. + "/requirements-${plone}-${python}.nix"
}:

let overrides = self: super: {

  "plone.recipe.zope2instance" = null;

  "astroid" = super."astroid".overridePythonAttrs(old: {
    src = fetchTarball {
      url = "https://github.com/PyCQA/astroid/archive/981a13962a0d3b2ca359d920dc94530650c15785.tar.gz";
      sha256 = "05wk2frac6nnnh4a0mys2fyawim430rx0qbkm9wcp2r0pzh2670c";
    };
  });

  "cffi" = super."cffi".overridePythonAttrs(old: {
    propagatedBuildInputs = [ self."pycparser" ];
  });

  "cryptography" = super."cryptography".overridePythonAttrs(old: {
    propagatedBuildInputs = [ self."asn1crypto" self."cffi" self."six" ];
  });

  "flake8" = super."flake8".overridePythonAttrs(old: {
    doCheck = false;
  });

  "twisted" = super."twisted".overridePythonAttrs(old: {
    nativeBuildInputs = [
      self."attrs"
      self."constantly"
      self."incremental"
      self."zope.interface"
    ];
  });

  # TODO: add to setup.nix default overrides
  "lazy-object-proxy" = super."lazy-object-proxy".overridePythonAttrs(old: {
    nativeBuildInputs = [ self."setuptools-scm" ];
  });

  # TODO: why tests failed with Plone 4.3 versions...
  "funcsigs" = super."funcsigs".overridePythonAttrs(old: {
    doCheck = false;
  });

  # TODO: why tests failed with Plone 4.3 versions...
  "mock" = super."mock".overridePythonAttrs(old: {
    doCheck = false;
  });

  "plone.testing" = super."plone.testing".overridePythonAttrs(old: {
    postPatch = if old.name == "plone.testing-4.1.2" then ''
      sed -i "s|from Testing.ZopeTestCase.ZopeLite import _patched as ZOPETESTCASEALERT||g" src/plone/testing/z2.py
      sed -i "s|if ZOPETESTCASEALERT|from Testing.ZopeTestCase.ZopeLite import _patched as ZOPETESTCASEALERT\n        if ZOPETESTCASEALERT|g" src/plone/testing/z2.py
    '' else ''
      sed -i "s|from Testing.ZopeTestCase.ZopeLite import _patched as ZOPETESTCASEALERT||g" src/plone/testing/zope.py
      sed -i "s|if ZOPETESTCASEALERT|from Testing.ZopeTestCase.ZopeLite import _patched as ZOPETESTCASEALERT\n        if ZOPETESTCASEALERT|g" src/plone/testing/zope.py
    '';
  });

  # should be fixed by updating jsonschema
  "jsonschema" = super."jsonschema".overridePythonAttrs(old: {
    nativeBuildInputs = [ self."vcversioner" self."setuptools-scm" ];
  });

  # should be fixed by updating nixpkgs
  "testfixtures" = super."testfixtures".overridePythonAttrs(old: {
    patches = [];
  });

  wheel = pythonPackages."wheel".overridePythonAttrs(old:
    with super."wheel"; { inherit propagatedBuildInputs; }
  );

  # fix zc.buildout to generate scripts with nix wrapped python env
  "zc.buildout" = pythonPackages.zc_buildout_nix.overridePythonAttrs (old: {
    name = super."zc.buildout".name;
    src = super."zc.buildout".src;
    postInstall = ''
      sed -i "s|import sys|import sys\nimport os\nsys.executable = os.path.join(sys.prefix, 'bin', os.path.basename(sys.executable))|" $out/bin/buildout
    '';
  });

  # fix zc.recipe.egg to support zip-installed setuptools
  "zc.recipe.egg" = super."zc.recipe.egg".overridePythonAttrs (old: {
    postPatch = if !pythonPackages.isPy27 then ''
      sed -i "s|return copy.deepcopy(cache_storage\[cache_key\])|import copyreg; import zipimport; copyreg.pickle(zipimport.zipimporter, lambda x: (x.__class__, (x.archive, ))); return copy.deepcopy(cache_storage[cache_key])|g" src/zc/recipe/egg/egg.py
    '' else "";
  });

};

in setup {
  inherit pkgs pythonPackages overrides;
  src = requirements;
  requirements = requirements;
  buildInputs = with pkgs; [
    firefox
    geckodriver
    redis
  ];
  force = true;
  shellHook = ''
    export PYTHONPATH=$(pwd)/src:$PYTHONPATH
    export PLONE=${plone}
    export PYTHON=${python}
  '';
}
