{
  pkgs,
  callPackage,
  nix,
  nix-pyenv-directory,
  pyenv,
  usingPython,
  inputDerivation ? "",
  ...
}:
let
  sitePackagesString = usingPython.sitePackages;
  nixPyenv = callPackage ./nix-pyenv.nix { inherit pyenv sitePackagesString inputDerivation; };
in
''
  ${nix}/bin/nix-store --add-root ./${nix-pyenv-directory} --realise ${nixPyenv}
''
