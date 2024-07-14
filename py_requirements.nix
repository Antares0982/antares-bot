pkgs: pypkgs: with pypkgs;
[
  (python-telegram-bot.overrideAttrs (super: {
    src = pkgs.fetchFromGitHub {
      # antares-ptb
      owner = "Antares0982";
      repo = "python-telegram-bot";
      rev = "v21.3";
      sha256 = "sha256-oCkwqN259q40L4FAReFySgbMjPi/GWuGmZP6PC+6VFw=";
    };
    doCheck = false;
    doInstallCheck = false;
    propagatedBuildInputs = super.propagatedBuildInputs ++ (with pypkgs;[ hatchling ]);
  }))
  aiosqlite
  objgraph
  aio-pika # optional
]
