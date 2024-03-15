rm -r tsunami
find . -empty -type d -delete  # remove empty directories to avoid wrong hashes
autonomy packages lock
autonomy fetch --local --agent dvilela/tsunami && cd tsunami

# Replace aea-config with the configured one
aeaconfig="/home/david/Descargas/aea-config.yaml"
if [ -e "$aeaconfig" ]; then
  cp $aeaconfig .
fi

cp $PWD/../ethereum_private_key.txt .
autonomy add-key ethereum ethereum_private_key.txt
autonomy issue-certificates
aea -s run