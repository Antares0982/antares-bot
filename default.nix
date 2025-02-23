{
  fetchFromGitHub,
  buildPythonPackage,
  pythonOlder,
  builder ? buildPythonPackage,
  aiosqlite,
  aio-pika,
  apscheduler,
  hatchling,
  objgraph,
  python-telegram-bot,
  pytz,
  setuptools,
  setuptools-scm,
  ...
}:
builder {
  pname = "antares-bot";
  version = "0.1.0";
  src = ./.;
  pyproject = true;
  build-system = [
    setuptools
    setuptools-scm
  ];
  disabled = pythonOlder "3.10";

  dependencies = [
    (python-telegram-bot.overrideAttrs (super: {
      src = fetchFromGitHub (import ./ptb-version.nix);
      doCheck = false;
      doInstallCheck = false;
      propagatedBuildInputs = super.propagatedBuildInputs ++ [ hatchling ];
    }))
    aiosqlite
    objgraph
    apscheduler
    pytz
    aio-pika
  ];
}
