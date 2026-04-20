{
  description = "WX Watcher custom component development environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-parts = {
      url = "github:hercules-ci/flake-parts";
      inputs.nixpkgs-lib.follows = "nixpkgs";
    };
    git-hooks-nix = {
      url = "github:cachix/git-hooks.nix";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.flake-compat.follows = "";
    };
  };

  outputs =
    inputs@{ flake-parts, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } {
      imports = [ inputs.git-hooks-nix.flakeModule ];
      systems = [ "x86_64-linux" ];

      perSystem =
        {
          config,
          lib,
          pkgs,
          ...
        }:
        let
          pch = pkgs.python3Packages.pre-commit-hooks;

          yamllintDefaultConfig = pkgs.writeText "yamllint-default-config" ''
            rules:
              document-start: disable
          '';

          yamllintWrapper = pkgs.writeShellApplication {
            name = "yamllint-wrapper";
            text = ''
              if [ -z "''${YAMLLINT_CONFIG_FILE:-}" ]; then
                export YAMLLINT_CONFIG_FILE="${yamllintDefaultConfig}"
              fi
              exec ${pkgs.yamllint}/bin/yamllint "$@"
            '';
          };

          forbidBinaryScript = pkgs.writeShellApplication {
            name = "forbid-binary";
            text = ''
              status=0
              for file in "$@"; do
                echo "Binary file detected: $file" >&2
                status=1
              done
              exit "$status"
            '';
          };

          scriptMustHaveExtensionScript = pkgs.writeShellApplication {
            name = "script-must-have-extension";
            text = ''
              status=0
              for file in "$@"; do
                if [[ "$file" != *.sh ]]; then
                  echo "Non-executable shell script must have .sh extension: $file" >&2
                  status=1
                fi
              done
              exit "$status"
            '';
          };

          scriptMustNotHaveExtensionScript = pkgs.writeShellApplication {
            name = "script-must-not-have-extension";
            text = ''
              status=0
              for file in "$@"; do
                if [[ "$file" == *.sh ]]; then
                  echo "Executable shell script should not have .sh extension: $file" >&2
                  status=1
                fi
              done
              exit "$status"
            '';
          };
        in
        {
          pre-commit.settings = {
            hooks = {
              # --- Formatters (base) ---
              nixfmt.enable = true;
              prettier = {
                enable = true;
                excludes = [ "\\.lock" ];
              };
              end-of-file-fixer = {
                enable = true;
                entry = "${pch}/bin/end-of-file-fixer";
                types = [ "text" ];
              };
              trim-trailing-whitespace = {
                enable = true;
                entry = "${pch}/bin/trailing-whitespace-fixer";
                types = [ "text" ];
              };
              mixed-line-ending = {
                enable = true;
                entry = "${pch}/bin/mixed-line-ending";
                types = [ "text" ];
              };
              fix-byte-order-marker = {
                enable = true;
                entry = "${pch}/bin/fix-byte-order-marker";
                types = [ "text" ];
              };

              # --- Formatters (python) ---
              ruff-format.enable = true;

              # --- Linters (base) ---
              nil.enable = true;
              statix.enable = true;
              shellcheck = {
                enable = true;
                excludes = [ "\\.envrc" ];
              };
              check-json.enable = true;
              check-toml.enable = true;
              check-yaml.enable = true;
              yamllint = {
                enable = true;
                entry = lib.mkForce "${yamllintWrapper}/bin/yamllint-wrapper";
                excludes = [ "\\.lock" ];
              };
              check-merge-conflict = {
                enable = true;
                entry = "${pch}/bin/check-merge-conflict";
                types = [ "text" ];
              };
              check-symlinks.enable = true;
              check-case-conflicts.enable = true;
              check-executables-have-shebangs.enable = true;
              check-shebang-scripts-are-executable = {
                enable = true;
                excludes = [ "\\.envrc" ];
              };

              # --- Linters (python) ---
              ruff.enable = true;

              # --- Custom hooks (base) ---
              forbid-binary = {
                enable = true;
                entry = "${forbidBinaryScript}/bin/forbid-binary";
                types = [ "binary" ];
                excludes = [ "brand/icon\\.png$" ];
                language = "system";
              };
              script-must-have-extension = {
                enable = true;
                entry = "${scriptMustHaveExtensionScript}/bin/script-must-have-extension";
                types = [ "shell" ];
                exclude_types = [ "executable" ];
                excludes = [ "\\.envrc" ];
                language = "system";
              };
              script-must-not-have-extension = {
                enable = true;
                entry = "${scriptMustNotHaveExtensionScript}/bin/script-must-not-have-extension";
                types = [
                  "shell"
                  "executable"
                ];
                language = "system";
              };

              # --- Custom hooks (project) ---
              mypy = {
                enable = true;
                entry = "uv run mypy custom_components/wx_watcher tests";
                files = "\\.py$";
                language = "system";
                types = [ "python" ];
                pass_filenames = false;
              };
              pytest = {
                enable = true;
                entry = "uv run pytest tests/ -v";
                files = "\\.py$";
                language = "system";
                types = [ "python" ];
                pass_filenames = false;
              };
            };
          };

          devShells.default = pkgs.mkShell {
            inputsFrom = [ config.pre-commit.devShell ];

            packages = with pkgs; [
              python313
              uv
            ];

            shellHook = ''
              uv sync --frozen --group test --group dev
            '';
          };
        };
    };
}
