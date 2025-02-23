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
      src = fetchFromGitHub {
        # antares-ptb
        owner = "Antares0982";
        repo = "python-telegram-bot";
        rev = "v21.10";
        sha256 = "sha256-RwOroSWXB3TF4mzTOOrAo+j0Abuq9LmATXSuGaO8j6U=";
      };
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
