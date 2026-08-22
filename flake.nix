{
  description = "AntaresBot Nix Flake";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs =
    inputs@{ self, nixpkgs }:
    let
      # nixpkgs' pythonMetadataCheckPhase rejects these: the upstream aiormq /
      # aio-pika release tags carry a pyproject version that differs from the tag.
      pythonMetadataFixes = final: prev: {
        pythonPackagesExtensions = prev.pythonPackagesExtensions ++ [
          (pyfinal: pyprev: {
            aiormq = pyprev.aiormq.overrideAttrs { dontCheckPythonMetadata = true; };
            aio-pika = pyprev.aio-pika.overrideAttrs { dontCheckPythonMetadata = true; };
          })
        ];
      };
      forAllSystems =
        function:
        nixpkgs.lib.genAttrs
          [
            "x86_64-linux"
            "aarch64-linux"
            "aarch64-darwin"
          ]
          (
            system:
            function (
              import nixpkgs {
                inherit system;
                overlays = [ pythonMetadataFixes ];
              }
            )
          );
    in
    rec {
      packages = forAllSystems (
        pkgs:
        let
          inherit (pkgs) python3Packages;
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
        default = pkgs.callPackage ./shell.nix { };
      });
      checks = packages;
    };
}
