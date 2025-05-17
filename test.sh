nix build .#ptb
cp -r --no-preserve=mode ./result/lib/python3.12/site-packages/telegram ./telegram
rm result
