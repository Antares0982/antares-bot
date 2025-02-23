{ pkgs, ... }:
pypkgs: with pypkgs; [
  (python-telegram-bot.overrideAttrs (super: {
    src = pkgs.fetchFromGitHub (import ./ptb-src.nix);
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
