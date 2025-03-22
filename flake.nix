{
  description = "AntaresBot Nix Flake";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs =
    inputs@{ self, nixpkgs }:
    let
      forAllSystems =
        function:
        nixpkgs.lib.genAttrs
          [
            "x86_64-linux"
            "aarch64-linux"
            "x86_64-darwin"
            "aarch64-darwin"
          ]
          (
            system:
            function (
              import nixpkgs {
                inherit system;
              }
            )
          );
    in rec
    {
      apps = forAllSystems (
        pkgs:
        let
          python3Packages = pkgs.python3Packages;
        in
        {
          default = python3Packages.callPackage ./. {
            builder = python3Packages.buildPythonApplication;
          };
        }
      );
      packages = forAllSystems (
        pkgs:
        let
          python3Packages = pkgs.python3Packages;
        in
        {
          default = python3Packages.callPackage ./. { };
          ptb = python3Packages.python-telegram-bot.overrideAttrs {
            src = pkgs.fetchFromGitHub (import ./ptb-src.nix);
            doInstallCheck = false;
          };
        }
      );
      modules.default = import ./.;
      devShells = forAllSystems (pkgs: {
        default = pkgs.callPackage ./shell.nix { persist = true; };
      });
      checks = packages;
    };
}
