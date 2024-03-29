if test -d tsunami; then
  echo "Removing previous agent build"
  rm -r tsunami
fi

find . -empty -type d -delete  # remove empty directories to avoid wrong hashes
autonomy packages lock
autonomy fetch --local --agent dvilela/tsunami
python scripts/aea-config-replace.py
cd tsunami
cp $PWD/../ethereum_private_key.txt .
autonomy add-key ethereum ethereum_private_key.txt
autonomy issue-certificates
aea -s run