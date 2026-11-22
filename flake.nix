{
  description = "AntaresBot Nix Flake";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
    };
    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
    };
  };

  outputs =
    {
      nixpkgs,
      pyproject-nix,
      uv2nix,
      pyproject-build-systems,
      ...
    }:
    let
      inherit (nixpkgs) lib;
      forAllSystems = lib.genAttrs [
        "x86_64-linux"
        "aarch64-linux"
        "aarch64-darwin"
      ];
      workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };
      overlay = workspace.mkPyprojectOverlay { sourcePreference = "wheel"; };
      pythonSets = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        (pkgs.callPackage pyproject-nix.build.packages { python = pkgs.python314; }).overrideScope (
          lib.composeManyExtensions [
            pyproject-build-systems.overlays.wheel
            overlay
          ]
        )
      );
    in
    rec {
      packages = forAllSystems (
        system:
        let
          pythonSet = pythonSets.${system};
        in
        {
          default = pythonSet.mkVirtualEnv "antares-bot" {
            antares-bot = [
              "pika"
              "webhooks"
            ];
          };
          ptb = pythonSet.antares-ptb;
        }
      );
      checks = packages;
      devShells = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          editable = pythonSets.${system}.overrideScope (
            workspace.mkEditablePyprojectOverlay { root = "$REPO_ROOT"; }
          );
          venv = editable.mkVirtualEnv "antares-bot-dev" workspace.deps.all;
        in
        {
          default = pkgs.mkShell {
            packages = [
              venv
              pkgs.uv
              pkgs.pyright
              pkgs.ruff
            ];
            env = {
              UV_NO_SYNC = "1";
              UV_PYTHON = "${venv}/bin/python";
              UV_PYTHON_DOWNLOADS = "never";
            };
            shellHook = ''
              unset PYTHONPATH
              export REPO_ROOT="$(git rev-parse --show-toplevel)"
              ${pkgs.nix}/bin/nix-store --add-root "$REPO_ROOT/.nix-pyenv" --realise ${venv} >/dev/null
            '';
          };
        }
      );
    };
}
