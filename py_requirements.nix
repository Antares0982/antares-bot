{ pkgs, ... }:
pypkgs: with pypkgs; [
  (python-telegram-bot.overrideAttrs (super: {
    # src = pkgs.fetchPypi {
    #   version = "v21.6";
    #   pname = "antares-ptb";
    #   hash = "";
    # };
    src = pkgs.fetchFromGitHub {
      # antares-ptb
      owner = "Antares0982";
      repo = "python-telegram-bot";
      rev = "v21.7";
      sha256 = "sha256-PMoJ3cSgLscUtiPf5JuxBM7exlqg7GTEX53KOUMaPeE=";
    };
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
