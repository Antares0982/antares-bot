{ pkgs, ... }:
pypkgs: with pypkgs; [
  (python-telegram-bot.overrideAttrs (super: {
    src = pkgs.fetchFromGitHub (import ./ptb-src.nix);
    doInstallCheck = false;
    # the fork ships as antares_ptb, so pname no longer matches its METADATA
    dontCheckPythonMetadata = true;
  }))
  aiosqlite
  objgraph
  # deps for job-queue
  apscheduler
  pytz
  # optional
  aio-pika
  # test
  pytest
  pytest-asyncio
]
