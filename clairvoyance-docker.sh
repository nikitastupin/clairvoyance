# Run clairvoyance in ephemeral docker container
# Mounts $PWD to /tmp/ for passing files, e.g.
# Save output: -o /tmp/schema.json
# Using wordlist: -w /tmp/wordlist.txt
docker run --rm -v $(pwd):/tmp/ nikitastupin/clairvoyance "$@"
