{
  description = "collective.taskqueue devenv";

  inputs = {
    devenv.url = "github:cachix/devenv/latest";
    flake-compat = {
      url = "github:edolstra/flake-compat";
      flake = false;
    };
    flake-utils.url = "github:numtide/flake-utils";
    nixpkgs.url = "github:NixOS/nixpkgs";
  };

  outputs = { self, ... }@inputs:
    inputs.flake-utils.lib.eachDefaultSystem (system:
      let pkgs = import inputs.nixpkgs { inherit system; };
      in {
        devShells.default = pkgs.mkShell {
          buildInputs = [ inputs.devenv.packages.${system}.devenv ];
          shellHook = ''
            devenv shell
          '';
        };
        formatter = pkgs.nixfmt;
      });
}
