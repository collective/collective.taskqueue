{ pkgs, ... }:

{
  # https://devenv.sh/basics/
  env.GREET = "devenv";

  # https://devenv.sh/packages/
  packages = [ pkgs.git ];

  # https://devenv.sh/scripts/
  scripts.hello.exec = "echo hello from $GREET";

  enterShell = ''
    hello
    git --version
  '';


  # https://devenv.sh/languages/
  languages.python.enable = true;
  languages.python.version = "3.11";
  languages.python.venv.enable = true;
  languages.python.venv.requirements = builtins.readFile 
  ./requirements.txt;

  # https://devenv.sh/pre-commit-hooks/
  # pre-commit.hooks.shellcheck.enable = true;

  # https://devenv.sh/processes/
  # processes.ping.exec = "ping example.com";

  # See full reference at https://devenv.sh/reference/options/
  services.redis.enable = true;
  services.mailhog.enable = true;

  devcontainer.enable = true;
}
