pkgs: pypkgs: with pypkgs;
[
  (python-telegram-bot.overrideAttrs (super: {
    src = pkgs.fetchFromGitHub {
      # antares-ptb
      owner = "Antares0982";
      repo = "python-telegram-bot";
      rev = "v21.4";
      sha256 = "sha256-aW+i3b902SxR6dWPwl9Q7MJZfhlrUG4HZdcLaPEK+KY=";
    };
    doCheck = false;
    doInstallCheck = false;
    propagatedBuildInputs = super.propagatedBuildInputs ++ (with pypkgs;[ hatchling ]);
  }))
  aiosqlite
  objgraph
  # deps for job-queue
  apscheduler
  pytz
  # optional
  aio-pika
]
