{
  pkgs,
  stdenvNoCC,
  pyenv,
  sitePackagesString,
  inputDerivation,
  ...
}:
stdenvNoCC.mkDerivation {
  name = "nix-pyenv";
  script = "";

  phases = [ "installPhase" ];

  installPhase = ''
    mkdir -p $out/bin
    mkdir -p $out/lib

    # creating python library symlinks
    for file in ${pyenv}/${sitePackagesString}/*; do
        basefile=$(basename $file)
        if [ -d "$file" ]; then
            if [[ "$basefile" != *dist-info && "$basefile" != __pycache__ ]]; then
                ln -s "$file" "$out/lib/$basefile"
            fi
        else
            # the typing_extensions.py will make the vscode type checker not working!
            if [[ $basefile == *.so ]] || ([[ $basefile == *.py ]] && [[ $basefile != typing_extensions.py ]]); then
                ln -s "$file" "$out/lib/$basefile"
            fi
        fi
    done
    for file in $out/lib/*; do
        if [[ -L "$file" ]] && [[ "$(dirname $(readlink "$file"))" != "${pyenv}/${sitePackagesString}" ]]; then
            rm -f "$file"
        fi
    done

    # ensure the typing_extensions.py is not in the lib directory
    rm -f $out/lib/typing_extensions.py

    ln -s "${pyenv}/bin/python" "$out/bin/python"
    ln -s "${inputDerivation}" "$out/bin/nix-shell-inputs"
  '';
}
