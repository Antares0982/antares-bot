{ pkgs, ... }:
pypkgs: with pypkgs; [
  (python-telegram-bot.overrideAttrs (super: {
    # src = pkgs.fetchPypi {
    #   version = "v21.6";
    #   pname = "antares-ptb";
    #   hash = "";
    # };
    src = pkgs.fetchFromGitHub (import ./ptb-version.nix);
    doCheck = false;
    doInstallCheck = false;
    propagatedBuildInputs = super.propagatedBuildInputs ++ (with pypkgs; [ hatchling ]);
  }))
  aiosqlite
  objgraph
  # deps for job-queue
  apscheduler
  pytz
  # optional
  aio-pika
]
