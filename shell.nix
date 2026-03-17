{
  pkgs ? import <nixpkgs> { },
  lib ? pkgs.lib,
  mkShell ? pkgs.mkShell,
  callPackage ? pkgs.callPackage,
}:
let
  optionalAttrs = lib.attrsets.optionalAttrs;
  # define the nix-pyenv directory
  nix-pyenv-directory = ".nix-pyenv";
  # define version
  usingPython = pkgs.python314;
  # import required python packages
  requiredPythonPackages = callPackage ./py_requirements.nix { };
  # create python environment
  pyenv = usingPython.withPackages requiredPythonPackages;
  #
  callShellHookParam = {
    inherit
      nix-pyenv-directory
      pyenv
      usingPython
      pkgs
      ;
  };
  internalShell = mkShell ({
    packages = [ pyenv ];
  });
in
internalShell.overrideAttrs {
  shellHook = callPackage ./shellhook.nix (
    callShellHookParam
    // {
      inherit (internalShell) inputDerivation;
    }
  );
}
