{
  fetchFromGitHub,
  python3Packages,
  buildPythonPackage,
  buildPythonApplication,
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
        rev = "v21.5";
        sha256 = "sha256-xQLaiMh+O8NGHSgGvQVPzsXxfbN60EmIhYTRaDd2zPg=";
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
