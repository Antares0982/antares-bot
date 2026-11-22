set -eu
ptb=$(nix build .#ptb --no-link --print-out-paths)
cp -RL --no-preserve=mode "$ptb"/lib/python*/site-packages/telegram/. ./telegram
