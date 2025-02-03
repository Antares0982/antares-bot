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
    in
    {
      apps = forAllSystems (pkgs: rec {
        default = pkgs.callPackage ./. (
          pkgs.python3Packages // { builder = pkgs.python3Packages.buildPythonApplication; }
        );
      });
      packages = forAllSystems (pkgs: rec {
        default = pkgs.callPackage ./. (
          pkgs.python3Packages // { builder = pkgs.python3Packages.buildPythonPackage; }
        );
      });
      modules.default = import ./.;
    };
}
