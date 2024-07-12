pkgs: pypkgs: with pypkgs;
[
  (python-telegram-bot.overrideAttrs {
    src = pkgs.fetchFromGitHub {
      owner = "Antares0982";
      repo = "python-telegram-bot";
      rev = "v21.3";
      sha256 = "sha256-GN27mhR1V0jpI8MSsPLBUbdVQbQOKh4l29kwZ7yrACY=";
    };
    doCheck = false;
    doInstallCheck = false; 
  })
  aiosqlite
  objgraph
  aio-pika  # optional
]
