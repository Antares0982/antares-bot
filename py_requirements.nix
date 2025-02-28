{ pkgs, ... }:
pypkgs: with pypkgs; [
  (python-telegram-bot.overrideAttrs (super: {
    src = pkgs.fetchFromGitHub (import ./ptb-src.nix);
    doInstallCheck = false;
  }))
  aiosqlite
  objgraph
  # deps for job-queue
  apscheduler
  pytz
  # optional
  aio-pika
]
